#include "veins/veins.h"

#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"
#include "veins/base/utils/SimpleAddress.h"

#include "VehicleApp.h"
#include "IPFEIAMsgs_m.h"

#include <cmath>
#include <cstring>
#include <sstream>

using namespace veins;

Define_Module(veins::VehicleApp);

namespace {
bool idInList(const std::string& id, const std::string& list)
{
    std::stringstream ss(list);
    std::string tok;
    while (std::getline(ss, tok, ';')) {
        if (tok == id) return true;
    }
    return false;
}
} // namespace

void VehicleApp::initialize(int stage)
{
    DemoBaseApplLayer::initialize(stage);
    if (stage == 0) {
        cc.readParams(this);
        eta = par("eta");
        n = par("n");
        maxRetries = par("maxAuthRetries");
        reportInterval = par("reportInterval");
        reauthInterval = par("reauthInterval");
        authTimeout = par("authTimeout");
        keyReqInterval = par("keyReqInterval");
        signEg1Count = par("signEg1Count");
        signBMCount = par("signBMCount");
        authMsgBytes = par("authMsgBytes");

        state = WAIT_KEYS;
        round = 0;
        simStart = simTime();
        ipfeiaLogHeader();

        scheduleAt(simTime() + uniform(0.05, 0.2), new cMessage("keyReq", KIND_KEY_REQ));
        scheduleAt(simTime() + 1, new cMessage("chanLog", KIND_CHAN_LOG));
    }
    else if (stage == 1) {
        // myId (the MAC address) is assigned by the base class in stage 1, so the
        // vehicle id must be derived here -- not in stage 0 (where it would be 0
        // for every vehicle)
        vehicleId = std::to_string(myId);
    }
}

void VehicleApp::finish()
{
    std::cout << "IPFEIA_LOG,VEH_SUMMARY," << vehicleId << "," << authOkCount << "," << authFailCount << ","
              << ctSent << "," << totalBytesSent << "," << (everAuthed ? 1 : 0) << std::endl;
    DemoBaseApplLayer::finish();
}

void VehicleApp::handleSelfMsg(cMessage* msg)
{
    switch (msg->getKind()) {
    case KIND_KEY_REQ: {
        if (state == WAIT_KEYS) {
            if ((int) keyRsus.size() >= eta) {
                if (lastRsuAddr == LAddress::L2BROADCAST()) {
                    // no RSU discovered yet. With eta = 3 this cannot happen
                    // (partial keys come from RSUs that also beacon), but it does
                    // when eta = 0, i.e. for the competitors that skip the key
                    // exchange; wait for a hello so the request is unicast.
                    scheduleAt(simTime() + keyReqInterval, msg);
                    return;
                }
                // vsk = H_1(V)^{k_i} * prod_j sk_{j,i}^{lambda_j}
                simtime_t vskDelay = cc.g1(eta, eta);
                vskReadyAt = simTime() + vskDelay;
                std::cout << "IPFEIA_LOG,VSK_READY," << vehicleId << "," << vskReadyAt.dbl() << ","
                          << (vskReadyAt - simStart).dbl() * 1000 << std::endl;
                startAuthentication(false, vskDelay);
                delete msg;
                return;
            }
            auto* req = new KeyRequest();
            req->setVehicleId(vehicleId.c_str());
            sendWsmDelayed(req, SIMTIME_ZERO, vehicleId.size() + 8, LAddress::L2BROADCAST());
            scheduleAt(simTime() + keyReqInterval, msg);
            return;
        }
        delete msg;
        break;
    }
    case KIND_AUTH_TIMEOUT: {
        if (state == AUTH_PENDING) {
            retries++;
            if (retries > maxRetries) {
                authFailCount++;
                std::cout << "IPFEIA_LOG,AUTH_FAIL," << vehicleId << "," << simTime().dbl() << ",timeout," << retries
                          << std::endl;
                // stay unauthenticated, retry from scratch after a while
                state = WAIT_KEYS;
                scheduleAt(simTime() + reauthInterval, new cMessage("keyReq", KIND_KEY_REQ));
            }
            else {
                // resend authentication request (same signing cost as the first attempt)
                simtime_t signDelay = cc.Eg1 * signEg1Count + cc.BM * signBMCount;
                auto* req = new AuthRequest();
                req->setVehicleId(vehicleId.c_str());
                req->setRound(round);
                int msgBytes = (authMsgBytes > 0) ? authMsgBytes : (2 * cc.g1Bytes + (int) vehicleId.size() + 8);
                sendWsmDelayed(req, signDelay, msgBytes, lastRsuAddr);
                authStart = simTime() + signDelay;
                scheduleAt(authStart + authTimeout, new cMessage("authTimeout", KIND_AUTH_TIMEOUT));
            }
        }
        delete msg;
        break;
    }
    case KIND_SEND_CT: {
        if (state == AUTHED) {
            // Enc: (2n+1) E_g1 + n M_g1 + 1 E_t
            simtime_t encDelay = cc.g1(2 * n + 1, n) + cc.Et;
            auto* ct = new CiphertextMsg();
            ct->setVehicleId(vehicleId.c_str());
            ct->setN(n);
            // (n+1) G1 elements + 1 G_T element
            sendWsmDelayed(ct, encDelay, (n + 1) * cc.g1Bytes + cc.gtBytes + 8, lastRsuAddr);
            ctSent++;
            std::cout << "IPFEIA_LOG,CT," << vehicleId << "," << (simTime() + encDelay).dbl() << "," << encDelay.dbl() * 1000 << std::endl;
        }
        scheduleAt(simTime() + reportInterval, msg);
        break;
    }
    case KIND_REAUTH: {
        if (state == AUTHED || state == WAIT_KEYS) startAuthentication(true);
        delete msg;
        break;
    }
    case KIND_CHAN_LOG: {
        logChan();
        totalBytesSent += bytesSent;
        bytesSent = 0;
        scheduleAt(simTime() + 1, msg);
        break;
    }
    default:
        DemoBaseApplLayer::handleSelfMsg(msg);
        break;
    }
}

void VehicleApp::startAuthentication(bool reauth, simtime_t computeDelay)
{
    round++;
    retries = 0;
    state = AUTH_PENDING;
    // vehicle-side cost of producing the authentication request. For the
    // proposed scheme this is already covered by the key combination; for the
    // signature-based one-to-one competitors it is the signing cost.
    simtime_t signDelay = cc.Eg1 * signEg1Count + cc.BM * signBMCount;
    computeDelay += signDelay;
    authStart = simTime() + computeDelay;
    if (reauth) {
        std::cout << "IPFEIA_LOG,REAUTH_START," << vehicleId << "," << authStart.dbl() << "," << round << ","
                  << curSpeed.length() * 3.6 << std::endl;
    }
    else {
        std::cout << "IPFEIA_LOG,AUTH_REQ," << vehicleId << "," << authStart.dbl() << "," << round << std::endl;
    }
    auto* req = new AuthRequest();
    req->setVehicleId(vehicleId.c_str());
    req->setRound(round);
    // T_i, K_i in G_1 (proposed scheme); the competitors use the message size
    // reported in the communication-cost comparison instead
    int msgBytes = (authMsgBytes > 0) ? authMsgBytes : (2 * cc.g1Bytes + (int) vehicleId.size() + 8);
    sendWsmDelayed(req, computeDelay, msgBytes, lastRsuAddr);
    scheduleAt(authStart + authTimeout, new cMessage("authTimeout", KIND_AUTH_TIMEOUT));
}

void VehicleApp::onWSM(BaseFrame1609_4* frame)
{
    totalBytesRecv += frame->getByteLength();
    if (auto* m = dynamic_cast<RsuHello*>(frame)) {
        handleRsuHello(m);
    }
    else if (auto* m = dynamic_cast<KeyResponse*>(frame)) {
        handleKeyResponse(m);
    }
    else if (auto* m = dynamic_cast<AuthBroadcast*>(frame)) {
        handleAuthBroadcast(m);
    }
    else if (auto* m = dynamic_cast<AuthAck*>(frame)) {
        handleAuthAck(m);
    }
    else if (dynamic_cast<CiphertextMsg*>(frame)) {
        // RSUs aggregate ciphertexts; a vehicle ignores other vehicles' reports
    }
}

void VehicleApp::handleRsuHello(RsuHello* m)
{
    LAddress::L2Type sender = senderOf(m);
    knownRsus[sender] = m->getRsuIndex();
    lastRsuAddr = sender;
}

void VehicleApp::handleKeyResponse(KeyResponse* m)
{
    if (state != WAIT_KEYS) return;
    if ((int) keyRsus.size() >= eta) return;
    if (keyRsus.count(m->getRsuIndex())) return; // already have this RSU's partial key
    keyRsus.insert(m->getRsuIndex());
    lastRsuAddr = senderOf(m);
    std::cout << "IPFEIA_LOG,KEY_GOT," << vehicleId << "," << simTime().dbl() << "," << m->getRsuIndex() << ","
              << keyRsus.size() << std::endl;
}

void VehicleApp::handleAuthBroadcast(AuthBroadcast* m)
{
    if (state != AUTH_PENDING) return;
    if (strcmp(m->getTargetVehicle(), "") != 0 && strcmp(m->getTargetVehicle(), vehicleId.c_str()) != 0) return;

    // the AS assigns the round id of the batch via the broadcast delta, so adopt
    // it here: every vehicle answered by the same broadcast then echoes the same
    // round id in its response, which is what makes the one-to-many batch work
    round = m->getRound();

    // verify delta: 5 E_g1 + 2 M_g1 + 1 BM + f2 evaluation over d coefficients.
    // A random backoff (CSMA/CA-style) spreads the responses of the whole
    // cohort over time instead of having them collide on the shared channel.
    simtime_t verifyDelay = cc.g1(5, 2) + cc.BM + cc.Mzr * m->getBatchD() + uniform(0, 0.5);

    auto* resp = new AuthResponse();
    resp->setVehicleId(vehicleId.c_str());
    resp->setRound(round);
    // sigma_i, T_i' in G_1
    sendWsmDelayed(resp, verifyDelay, 2 * cc.g1Bytes + vehicleId.size() + 8, lastRsuAddr);
    std::cout << "IPFEIA_LOG,DELTA_VERIFIED," << vehicleId << "," << (simTime() + verifyDelay).dbl() << "," << round
              << std::endl;
}

void VehicleApp::handleAuthAck(AuthAck* m)
{
    if (state != AUTH_PENDING) return;
    if (m->getRound() != round) return;
    if (!idInList(vehicleId, m->getAckedIds())) return;

    simtime_t latency = simTime() - authStart;
    bool initial = (authOkCount == 0);
    state = AUTHED;
    everAuthed = true;
    authOkCount++;
    std::cout << "IPFEIA_LOG,AUTH_OK," << vehicleId << "," << simTime().dbl() << "," << latency.dbl() * 1000 << ","
              << round << "," << (initial ? "initial" : "reauth") << std::endl;
    if (initial && vskReadyAt > 0) {
        std::cout << "IPFEIA_LOG,JOIN_DONE," << vehicleId << "," << simTime().dbl() << ","
                  << (simTime() - simStart).dbl() * 1000 << std::endl;
        vskReadyAt = 0;
    }

    scheduleAt(simTime() + 0.05, new cMessage("sendCt", KIND_SEND_CT));
    // re-authentication is periodic and synchronised to a global clock: the
    // fleet re-authenticates in bursts, which is the regime the one-to-many
    // broadcast authentication is designed for
    double ri = reauthInterval.dbl();
    double nextTick = (std::floor(simTime().dbl() / ri) + 1.0) * ri;
    scheduleAt(nextTick, new cMessage("reauth", KIND_REAUTH));
}

void VehicleApp::sendWsmDelayed(BaseFrame1609_4* wsm, simtime_t delay, int payloadBytes, LAddress::L2Type rcvId)
{
    populateWSM(wsm, rcvId);
    wsm->addByteLength(payloadBytes);
    bytesSent += payloadBytes + 10; // + MAC/phy header approximation
    if (delay == SIMTIME_ZERO) {
        sendDown(wsm);
    }
    else {
        sendDelayedDown(wsm, delay);
    }
}

void VehicleApp::logChan()
{
    std::cout << "IPFEIA_LOG,CHAN,veh" << vehicleId << "," << simTime().dbl() << "," << bytesSent << ",0" << std::endl;
}

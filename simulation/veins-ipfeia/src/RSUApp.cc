#include "veins/veins.h"

#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"
#include "veins/base/utils/SimpleAddress.h"

#include "RSUApp.h"
#include "IPFEIAMsgs_m.h"

using namespace veins;

Define_Module(veins::RSUApp);

void RSUApp::initialize(int stage)
{
    DemoBaseApplLayer::initialize(stage);
    if (stage == 0) {
        cc.readParams(this);
        aggWindow = par("aggWindow");
        backhaulDelay = par("backhaulDelay");
        helloInterval = par("helloInterval");
        aggMode = par("aggMode").stdstringValue();

        rsuIndex = getParentModule()->getIndex();
        asModule = getSimulation()->getSystemModule()->getSubmodule("as");
        ipfeiaLogHeader();

        scheduleAt(simTime() + uniform(0.05, 0.15), new cMessage("hello", KIND_RSU_HELLO));
        scheduleAt(simTime() + aggWindow, new cMessage("agg", KIND_RSU_AGG));
        scheduleAt(simTime() + 1, new cMessage("chanLog", KIND_CHAN_LOG));
    }
}

void RSUApp::finish()
{
    std::cout << "IPFEIA_LOG,RSU_SUMMARY," << rsuIndex << "," << aggCount << "," << totalBytesSent << ","
              << totalBytesRecv << std::endl;
    DemoBaseApplLayer::finish();
}

void RSUApp::handleMessage(cMessage* msg)
{
    if (msg->arrivedOn("backendIn")) {
        if (auto* b = dynamic_cast<BackBroadcast*>(msg)) {
            handleBackendBroadcast(b);
            return;
        }
        delete msg;
        return;
    }
    DemoBaseApplLayer::handleMessage(msg);
}

void RSUApp::handleSelfMsg(cMessage* msg)
{
    switch (msg->getKind()) {
    case KIND_RSU_HELLO: {
        auto* hello = new RsuHello();
        hello->setRsuIndex(rsuIndex);
        sendWsm(hello, 8, LAddress::L2BROADCAST());
        scheduleAt(simTime() + helloInterval, msg);
        break;
    }
    case KIND_RSU_AGG: {
        if (ctCount > 0) {
            int d = ctCount;
            // AggEnc: paper keeps the full d x n tuple (products of C_1, C_3 only);
            // "aggregated" multiplies the C_2 components as well (n*(d-1) M_g1)
            simtime_t aggDelay = (d - 1) * (cc.Mg1 + cc.Mt);
            if (aggMode == "aggregated") aggDelay += ctN * (d - 1) * cc.Mg1;

            auto* agg = new BackAggregate();
            agg->setD(d);
            agg->setN(ctN);
            // send after the aggregation computation plus the backhaul delay
            // (plain messages cannot carry a transmission duration, so only the
            //  propagation delay is set via SendOptions)
            sendDirect(agg, SendOptions().propagationDelay(aggDelay + backhaulDelay), asModule, "directIn");
            aggCount++;
            std::cout << "IPFEIA_LOG,RSU_AGG," << rsuIndex << "," << (simTime() + aggDelay).dbl() << "," << d << ","
                      << ctN << "," << aggDelay.dbl() * 1000 << std::endl;
            ctCount = 0;
        }
        scheduleAt(simTime() + aggWindow, msg);
        break;
    }
    case KIND_CHAN_LOG: {
        std::cout << "IPFEIA_LOG,CHAN,rsu" << rsuIndex << "," << simTime().dbl() << "," << bytesSent << ","
                  << bytesRecv << std::endl;
        totalBytesSent += bytesSent;
        totalBytesRecv += bytesRecv;
        bytesSent = 0;
        bytesRecv = 0;
        scheduleAt(simTime() + 1, msg);
        break;
    }
    default:
        DemoBaseApplLayer::handleSelfMsg(msg);
        break;
    }
}

void RSUApp::onWSM(BaseFrame1609_4* frame)
{
    if (auto* m = dynamic_cast<KeyRequest*>(frame)) {
        handleKeyRequest(m);
    }
    else if (auto* m = dynamic_cast<AuthRequest*>(frame)) {
        handleAuthRequest(m);
    }
    else if (auto* m = dynamic_cast<AuthResponse*>(frame)) {
        handleAuthResponse(m);
    }
    else if (auto* m = dynamic_cast<CiphertextMsg*>(frame)) {
        handleCiphertext(m);
    }
    else if (dynamic_cast<RsuHello*>(frame)) {
        // other RSUs' hellos are ignored
    }
    else if (auto* m = dynamic_cast<KeyResponse*>(frame)) {
        (void) m; // another RSU answered first; ignore
    }
    else if (auto* m = dynamic_cast<AuthAck*>(frame)) {
        (void) m;
    }
    else if (auto* m = dynamic_cast<AuthBroadcast*>(frame)) {
        (void) m;
    }
}

void RSUApp::handleKeyRequest(KeyRequest* m)
{
    bytesRecv += m->getByteLength();
    // partial key extract: H_1(V)^{c_i * rsk_j}. The response leaves after the
    // extraction computation; a small per-RSU processing jitter decorrelates the
    // replies of RSUs that hear the same request (otherwise they transmit at the
    // identical instant and mutually corrupt each other at the vehicle)
    simtime_t extractDelay = cc.Eg1 + uniform(0, 0.005);
    auto* resp = new KeyResponse();
    resp->setVehicleId(m->getVehicleId());
    resp->setRsuIndex(rsuIndex);
    sendWsm(resp, cc.g1Bytes + 8, senderOf(m), extractDelay);
    // NOTE: do NOT delete m -- DemoBaseApplLayer::handleLowerMsg() owns the frame
    // and deletes it after onWSM() returns (deleting here causes a double free).
}

void RSUApp::handleAuthRequest(AuthRequest* m)
{
    bytesRecv += m->getByteLength();
    vehAddrs[m->getVehicleId()] = senderOf(m);
    auto* fwd = new BackAuthRequest();
    fwd->setVehicleId(m->getVehicleId());
    fwd->setRound(m->getRound());
    fwd->setRsuIndex(rsuIndex);
    forwardToAS(fwd);
    // frame deleted by DemoBaseApplLayer::handleLowerMsg()
}

void RSUApp::handleAuthResponse(AuthResponse* m)
{
    bytesRecv += m->getByteLength();
    vehAddrs[m->getVehicleId()] = senderOf(m);
    auto* fwd = new BackAuthResponse();
    fwd->setVehicleId(m->getVehicleId());
    fwd->setRound(m->getRound());
    fwd->setRsuIndex(rsuIndex);
    forwardToAS(fwd);
    // frame deleted by DemoBaseApplLayer::handleLowerMsg()
}

void RSUApp::handleCiphertext(CiphertextMsg* m)
{
    bytesRecv += m->getByteLength();
    ctCount++;
    ctN = m->getN();
    vehAddrs[m->getVehicleId()] = senderOf(m);
    // frame deleted by DemoBaseApplLayer::handleLowerMsg()
}

void RSUApp::handleBackendBroadcast(BackBroadcast* b)
{
    if (b->getKindCode() == 1 || b->getKindCode() == 3) {
        auto* wsm = new AuthBroadcast();
        wsm->setRound(b->getRound());
        wsm->setBatchD(b->getBatchD());
        wsm->setTargetVehicle(b->getTargetVehicle());
        // delta: B = {b_0..b_{d-1}}, t_1, sigma (Z_q), T_2 (G_1)
        int payload = b->getBatchD() > 0 ? (b->getBatchD() + 2) * cc.zqBytes + cc.g1Bytes + cc.zqBytes
                                         : 3 * cc.zqBytes + cc.g1Bytes + cc.zqBytes;
        LAddress::L2Type rcv = LAddress::L2BROADCAST();
        if (b->getKindCode() == 3) {
            auto it = vehAddrs.find(b->getTargetVehicle());
            if (it != vehAddrs.end()) rcv = it->second;
            payload = 3 * cc.zqBytes + cc.g1Bytes + cc.zqBytes;
        }
        sendWsm(wsm, payload, rcv);
    }
    else if (b->getKindCode() == 2) {
        auto* wsm = new AuthAck();
        wsm->setRound(b->getRound());
        wsm->setAckedIds(b->getAckedIds());
        sendWsm(wsm, 8 * 10 + 16, LAddress::L2BROADCAST());
    }
    delete b;
}

void RSUApp::sendWsm(BaseFrame1609_4* wsm, int payloadBytes, LAddress::L2Type rcvId, simtime_t delay)
{
    populateWSM(wsm, rcvId);
    wsm->addByteLength(payloadBytes);
    bytesSent += payloadBytes + 10;
    if (delay == SIMTIME_ZERO) {
        sendDown(wsm);
    }
    else {
        sendDelayedDown(wsm, delay);
    }
}

void RSUApp::forwardToAS(cMessage* msg)
{
    sendDirect(msg, SendOptions().propagationDelay(backhaulDelay), asModule, "directIn");
}

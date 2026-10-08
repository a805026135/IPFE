#include "veins/veins.h"

#include "ASApp.h"
#include "IPFEIAMsgs_m.h"
#include <omnetpp/ccanvas.h>

#include <algorithm>

using namespace veins;

Define_Module(veins::ASApp);

void ASApp::initialize()
{
    // optional: paint a real-map background (1 px = 1 m) on the canvas so the
    // Qtenv view shows the actual road network the simulation runs on
    {
        const char* bgName = par("canvasBgImage").stdstringValue().c_str();
        if (bgName && *bgName) {
            cImageFigure* bg = new cImageFigure("campusBg");
            bg->setImageName(bgName);
            bg->setPosition(cFigure::Point(0, 0));
            bg->setAnchor(cFigure::ANCHOR_NW);
            // image covers exactly the playground rectangle (1 m grid)
            double pgsX = getParentModule()->par("playgroundSizeX").doubleValue();
            double pgsY = getParentModule()->par("playgroundSizeY").doubleValue();
            bg->setSize(pgsX, pgsY);
            bg->setZIndex(-1000);
            getParentModule()->getCanvas()->addFigure(bg);
        }
    }
    cc.readParams(this);
    authMode = par("authMode").stdstringValue();
    decMode = par("decMode").stdstringValue();
    batchWindow = par("batchWindow");
    ackWindow = par("ackWindow");
    backhaulDelay = par("backhaulDelay");
    dlRange = par("dlRange");
    n = par("n");
    o2oDeltaEg1 = par("o2oDeltaEg1");
    o2oDeltaBM = par("o2oDeltaBM");
    o2oVerifyEg1 = par("o2oVerifyEg1");
    o2oVerifyBM = par("o2oVerifyBM");
    ipfeiaLogHeader();
}

void ASApp::finish()
{
    std::cout << "IPFEIA_LOG,AS_SUMMARY," << simTime().dbl() << "," << authMode << "," << decMode << "," << batchCount
              << "," << authReqTotal << "," << respTotal << "," << ackTotal << "," << decMsgs << "," << decVehicles
              << "," << decDelaySum.dbl() * 1000 << "," << asBusy.dbl() * 1000 << "," << authBusy.dbl() * 1000 << ","
              << decBusy.dbl() * 1000 << std::endl;
}

void ASApp::handleMessage(cMessage* msg)
{
    if (auto* t = dynamic_cast<ASTimer*>(msg)) {
        handleTimer(t);
    }
    else if (auto* m = dynamic_cast<BackAuthRequest*>(msg)) {
        handleAuthRequest(m);
    }
    else if (auto* m = dynamic_cast<BackAuthResponse*>(msg)) {
        handleAuthResponse(m);
    }
    else if (auto* m = dynamic_cast<BackAggregate*>(msg)) {
        handleAggregate(m);
    }
    else {
        delete msg;
    }
}

void ASApp::handleAuthRequest(BackAuthRequest* m)
{
    authReqTotal++;

    if (authMode == "o2o") {
        // per-vehicle challenge/delta; the cost is configurable so that the same
        // path can also represent a signature-based one-to-one competitor
        // (which performs no AS-side delta, i.e. o2oDeltaEg1 = o2oDeltaBM = 0)
        simtime_t deltaDelay = cc.Eg1 * o2oDeltaEg1 + cc.BM * o2oDeltaBM;
        asBusy += deltaDelay;
        authBusy += deltaDelay;
        auto* b = new BackBroadcast();
        b->setKindCode(3); // per-vehicle delta, unicast through the RSU
        b->setRound(m->getRound());
        b->setBatchD(1);
        b->setTargetVehicle(m->getVehicleId());
        sendToRsu(b, m->getRsuIndex(), deltaDelay + backhaulDelay);
        std::cout << "IPFEIA_LOG,AS_DELTA," << (simTime() + deltaDelay).dbl() << "," << m->getRound() << ",1,"
                  << deltaDelay.dbl() * 1000 << ",o2o" << std::endl;
        delete m;
        return;
    }

    // one-to-many: collect into the active batch (one window per burst)
    if (!batchOpen) {
        batchOpen = true;
        activeBatch.vehicles.clear();
        activeBatch.responded.clear();
        activeRsus.clear();
        auto* t = new ASTimer();
        t->setWhat(WHAT_BATCH_WINDOW);
        scheduleAt(simTime() + batchWindow, t);
    }
    activeBatch.vehicles.push_back(m->getVehicleId());
    activeRsus.insert(m->getRsuIndex());
    delete m;
}

void ASApp::handleAuthResponse(BackAuthResponse* m)
{
    if (authMode == "o2o") {
        // verify one response: configurable (2 E_g1 + 1 BM for the proposed
        // scheme's one-to-one variant; a competitor's signature-verification
        // cost for the signature-based schemes)
        simtime_t verifyDelay = cc.Eg1 * o2oVerifyEg1 + cc.BM * o2oVerifyBM;
        asBusy += verifyDelay;
        authBusy += verifyDelay;
        auto* t = new ASTimer();
        t->setWhat(WHAT_O2O_VERIFY);
        t->setRound(m->getRound());
        t->setVehicleId(m->getVehicleId());
        t->setRsuIndex(m->getRsuIndex());
        scheduleAt(simTime() + verifyDelay, t);
        delete m;
        return;
    }

    // late responses (after the ack window closed) are dropped; the vehicle
    // will time out and retry
    if (!batchOpen) {
        delete m;
        return;
    }
    if (m->getRound() != currentRound) {
        delete m;
        return;
    }
    // The delta was broadcast to every vehicle in range, so a response is
    // accepted from any vehicle that echoes the current batch round -- that is
    // exactly what lets a single broadcast authenticate the whole responding
    // cohort (one-to-many authentication).
    activeBatch.responded.insert(m->getVehicleId());
    delete m;
}

void ASApp::handleAggregate(BackAggregate* m)
{
    int d = m->getD();
    int nn = (m->getN() > 0) ? m->getN() : n;
    // Dec = n E_g1 + 2 BM + brute-force DL over a range of dlRange elements
    simtime_t unit = cc.g1(nn, 0) + 2 * cc.BM + cc.dl(dlRange);
    simtime_t decDelay = (decMode == "paper") ? unit * d : unit;
    asBusy += decDelay;
    decBusy += decDelay;
    decMsgs++;
    decVehicles += d;
    decDelaySum += decDelay;
    std::cout << "IPFEIA_LOG,AS_DEC," << (simTime() + decDelay).dbl() << "," << d << "," << nn << ","
              << decDelay.dbl() * 1000 << "," << decMode << std::endl;
    delete m;
}

void ASApp::handleTimer(ASTimer* t)
{
    switch (t->getWhat()) {
    case WHAT_BATCH_WINDOW: {
        if (activeBatch.vehicles.empty()) {
            batchOpen = false;
            break;
        }
        batchCount++;
        // one broadcast delta for the whole batch; AS cost is independent of d
        // apart from the M_zr coefficient picks: 2 E_g1 + 1 BM + d M_zr
        currentRound = ++asRound;
        int d = (int) activeBatch.vehicles.size();
        simtime_t deltaDelay = cc.g1(2, 0) + cc.BM + cc.Mzr * d;
        asBusy += deltaDelay;
        authBusy += deltaDelay;
        auto* b = new BackBroadcast();
        b->setKindCode(1);
        b->setRound(currentRound);
        b->setBatchD(d);
        sendToRsus(b, activeRsus, deltaDelay + backhaulDelay);
        std::cout << "IPFEIA_LOG,AS_DELTA," << (simTime() + deltaDelay).dbl() << "," << currentRound << "," << d << ","
                  << deltaDelay.dbl() * 1000 << ",o2m" << std::endl;
        auto* ack = new ASTimer();
        ack->setWhat(WHAT_ACK_WINDOW);
        scheduleAt(simTime() + ackWindow, ack);
        break;
    }
    case WHAT_ACK_WINDOW: {
        int d = (int) activeBatch.vehicles.size();
        int resp = (int) activeBatch.responded.size();
        if (resp > 0) {
            // aggregate verification of the whole batch in constant pairings:
            // 2 E_g1 + 2 BM + resp M_g1
            simtime_t verifyDelay = cc.g1(2, 0) + 2 * cc.BM + cc.Mg1 * resp;
            asBusy += verifyDelay;
            authBusy += verifyDelay;
            std::string acked;
            for (const auto& v : activeBatch.responded) {
                if (!acked.empty()) acked += ";";
                acked += v;
            }
            auto* b = new BackBroadcast();
            b->setKindCode(2);
            b->setRound(currentRound);
            b->setAckedIds(acked.c_str());
            sendToRsus(b, activeRsus, verifyDelay + backhaulDelay);
            respTotal += resp;
            ackTotal += resp;
            std::cout << "IPFEIA_LOG,AS_ACK," << (simTime() + verifyDelay).dbl() << "," << currentRound << "," << resp
                      << "," << d << ",o2m" << std::endl;
        }
        activeBatch.vehicles.clear();
        activeBatch.responded.clear();
        activeRsus.clear();
        batchOpen = false;
        break;
    }
    case WHAT_O2O_VERIFY: {
        // acknowledge the single verified vehicle
        auto* b = new BackBroadcast();
        b->setKindCode(2);
        b->setRound(t->getRound());
        b->setAckedIds(t->getVehicleId());
        sendToRsu(b, t->getRsuIndex(), backhaulDelay);
        respTotal++;
        ackTotal++;
        std::cout << "IPFEIA_LOG,AS_ACK," << simTime().dbl() << "," << t->getRound() << ",1,1,o2o" << std::endl;
        break;
    }
    default:
        break;
    }
    delete t;
}

void ASApp::sendToRsu(BackBroadcast* b, int rsuIndex, simtime_t delay)
{
    cModule* rsu = getSimulation()->getSystemModule()->getSubmodule("rsu", rsuIndex);
    if (rsu) {
        // the backendIn gate lives on the RSU's RSUApp (rsu[i].appl), not on the
        // RSU node itself
        cModule* appl = rsu->getSubmodule("appl");
        if (appl) {
            sendDirect(b, SendOptions().propagationDelay(delay), appl, "backendIn");
            return;
        }
    }
    delete b;
}

void ASApp::sendToRsus(BackBroadcast* b, const std::set<int>& rsus, simtime_t delay)
{
    for (int idx : rsus) {
        BackBroadcast* copy = b->dup();
        sendToRsu(copy, idx, delay);
    }
    delete b;
}

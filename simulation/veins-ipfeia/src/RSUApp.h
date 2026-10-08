#pragma once

#include "veins/veins.h"

#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"
#include "IPFEIASupport.h"
#include "IPFEIAMsgs_m.h"

#include <map>
#include <string>
#include <vector>

using namespace omnetpp;

namespace veins {

/**
 * RSU-side application of the IPFE-IA protocol:
 *  - periodic hello beacon so vehicles learn nearby RSUs
 *  - partial key extraction for registering vehicles
 *  - relay of authentication traffic between vehicles and the AS
 *  - windowed aggregation of vehicle ciphertexts, forwarded to the AS
 */
class RSUApp : public DemoBaseApplLayer {
public:
    void initialize(int stage) override;
    void finish() override;

protected:
    enum SelfKinds {
        KIND_RSU_HELLO = 16800,
        KIND_RSU_AGG,
        KIND_CHAN_LOG,
    };

    void onWSM(BaseFrame1609_4* frame) override;
    void handleSelfMsg(cMessage* msg) override;
    void handleMessage(cMessage* msg) override; // catch backendIn before the base class

    void handleKeyRequest(KeyRequest* m);
    void handleAuthRequest(AuthRequest* m);
    void handleAuthResponse(AuthResponse* m);
    void handleCiphertext(CiphertextMsg* m);
    void handleBackendBroadcast(BackBroadcast* m);
    void sendWsm(BaseFrame1609_4* wsm, int payloadBytes, LAddress::L2Type rcvId, simtime_t delay = SIMTIME_ZERO);
    void forwardToAS(cMessage* msg);

    CryptoCosts cc;
    simtime_t aggWindow;
    simtime_t backhaulDelay;
    simtime_t helloInterval;
    std::string aggMode; // "paper" | "aggregated"

    int rsuIndex = 0;
    cModule* asModule = nullptr;
    std::map<std::string, LAddress::L2Type> vehAddrs; // vehicle id -> last known L2 address
    int ctCount = 0;
    int ctN = 0;
    int aggCount = 0;
    long bytesSent = 0;
    long bytesRecv = 0;
    long totalBytesSent = 0; // cumulative (bytesSent is reset every second by chanLog)
    long totalBytesRecv = 0;
};

} // namespace veins

#pragma once

#include "veins/veins.h"

#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"
#include "IPFEIASupport.h"
#include "IPFEIAMsgs_m.h"

#include <map>
#include <set>
#include <string>

using namespace omnetpp;

namespace veins {

/**
 * Vehicle-side application of the IPFE-IA protocol.
 *
 * State machine:
 *   WAIT_KEYS    broadcast key requests until eta partial keys from distinct
 *                RSUs are collected, then compute vsk
 *   AUTH_PENDING request mutual authentication with the AS (round r), verify
 *                the broadcast delta, respond, wait for the AS acknowledgement
 *   AUTHED       periodically encrypt and report ciphertexts, re-authenticate
 *                every reauthInterval
 */
class VehicleApp : public DemoBaseApplLayer {
public:
    void initialize(int stage) override;
    void finish() override;

protected:
    enum SelfKinds {
        KIND_KEY_REQ = 16384,
        KIND_AUTH_TIMEOUT,
        KIND_SEND_CT,
        KIND_REAUTH,
        KIND_CHAN_LOG,
    };
    enum State {
        WAIT_KEYS,
        AUTH_PENDING,
        AUTHED,
    };

    void onWSM(BaseFrame1609_4* frame) override;
    void handleSelfMsg(cMessage* msg) override;

    void startAuthentication(bool reauth, simtime_t computeDelay = SIMTIME_ZERO);
    void handleRsuHello(RsuHello* m);
    void handleKeyResponse(KeyResponse* m);
    void handleAuthBroadcast(AuthBroadcast* m);
    void handleAuthAck(AuthAck* m);
    void sendWsmDelayed(BaseFrame1609_4* wsm, simtime_t delay, int payloadBytes, LAddress::L2Type rcvId);
    void logChan();

    // parameters
    CryptoCosts cc;
    int eta;
    int n;
    int maxRetries;
    simtime_t reportInterval;
    simtime_t reauthInterval;
    simtime_t authTimeout;
    simtime_t keyReqInterval;
    int signEg1Count;  // vehicle-side signing cost of a competitor request
    int signBMCount;
    int authMsgBytes;  // 0 => native size of the proposed scheme

    // state
    State state;
    std::string vehicleId;
    std::set<int> keyRsus;                     // rsu indices that supplied partial keys
    std::map<LAddress::L2Type, int> knownRsus;  // heard RSUs: l2 address -> index
    LAddress::L2Type lastRsuAddr = LAddress::L2BROADCAST();
    int round = 0;
    int retries = 0;
    int authOkCount = 0;
    int authFailCount = 0;
    int ctSent = 0;
    long bytesSent = 0;
    long totalBytesSent = 0; // cumulative (bytesSent is reset every second by chanLog)
    long totalBytesRecv = 0;
    simtime_t authStart = 0;
    simtime_t simStart = 0;
    simtime_t vskReadyAt = 0;
    bool everAuthed = false;
};

} // namespace veins

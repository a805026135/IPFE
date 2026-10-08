#pragma once

#include "veins/veins.h"
#include "IPFEIASupport.h"
#include "IPFEIAMsgs_m.h"

#include <map>
#include <set>
#include <string>
#include <vector>

using namespace omnetpp;

namespace veins {

/**
 * Application server of the IPFE-IA protocol.
 *
 * Authentication (authMode):
 *  - "o2m" one-to-many: collects vehicle requests relayed by the RSUs within a
 *    batch window, broadcasts one delta per round group, then aggregate-verifies
 *    the collected responses in a constant number of pairings (2 E_g1 + 2 BM +
 *    m M_g1) and broadcasts the acknowledgement list.
 *  - "o2o" one-to-one baseline: per-vehicle delta and per-vehicle verification,
 *    i.e. AS cost grows linearly in the number of vehicles.
 *
 * Decryption (decMode):
 *  - "paper": d individual Dec executions, each n E_g1 + 2 BM + DL
 *  - "aggregated": one component-wise aggregated decryption, n E_g1 + 2 BM + DL
 */
class ASApp : public cSimpleModule {
public:
    void initialize() override;
    void finish() override;

protected:
    enum TimerWhat {
        WHAT_BATCH_WINDOW = 0, // batch collection window expired -> broadcast delta(s)
        WHAT_ACK_WINDOW = 1,   // response window expired -> aggregate verify + ack
        WHAT_O2O_VERIFY = 2,   // one-to-one: single response verification done
    };

    void handleMessage(cMessage* msg) override;
    void handleAuthRequest(BackAuthRequest* m);
    void handleAuthResponse(BackAuthResponse* m);
    void handleAggregate(BackAggregate* m);
    void handleTimer(ASTimer* t);
    void sendToRsu(BackBroadcast* b, int rsuIndex, simtime_t delay);
    void sendToRsus(BackBroadcast* b, const std::set<int>& rsus, simtime_t delay);

    CryptoCosts cc;
    std::string authMode; // "o2m" | "o2o"
    std::string decMode; // "paper" | "aggregated"
    simtime_t batchWindow;
    simtime_t ackWindow;
    simtime_t backhaulDelay;
    int dlRange;
    int n;
    // per-vehicle costs of the one-to-one path, in numbers of measured
    // primitives (used for the baseline and for the signature-based competitors)
    int o2oDeltaEg1;
    int o2oDeltaBM;
    int o2oVerifyEg1;
    int o2oVerifyBM;

    // vehicles collected in the current one-to-many batching window. The AS
    // assigns one round id per batch and broadcasts a single delta carrying it,
    // so all vehicles that authenticate concurrently share one broadcast.
    struct RoundGroup {
        std::vector<std::string> vehicles;
        std::set<std::string> responded;
    };
    RoundGroup activeBatch;
    std::set<int> activeRsus;
    bool batchOpen = false;
    int asRound = 0;      // monotonically increasing batch round id (assigned by the AS)
    int currentRound = 0; // round id of the batch currently being processed

    // statistics
    int batchCount = 0;
    int authReqTotal = 0;
    int respTotal = 0;
    int ackTotal = 0;
    int decMsgs = 0;
    int decVehicles = 0;
    simtime_t decDelaySum;
    simtime_t asBusy;   // cumulative AS computation time (authentication + decryption)
    simtime_t authBusy; // cumulative AS time spent on authentication only
    simtime_t decBusy;  // cumulative AS time spent on decryption only
};

} // namespace veins

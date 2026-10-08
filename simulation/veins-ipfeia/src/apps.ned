package ipfeia;

import org.car2x.veins.modules.application.ieee80211p.DemoBaseApplLayer;

//
// On-board unit application: registration (collect eta partial keys from
// distinct RSUs), mutual authentication with the AS, periodic ciphertext
// reporting to the nearest RSU.
//
simple VehicleApp extends DemoBaseApplLayer
{
    parameters:
        @class(veins::VehicleApp);
        // per-primitive crypto costs (measured, see crypto-bench/crypto_params.ini)
        double cryptoEg1 @unit(ms) = default(5.5ms);
        double cryptoMg1 @unit(ms) = default(0.03ms);
        double cryptoEg2 @unit(ms) = default(5.5ms);
        double cryptoMg2 @unit(ms) = default(0.03ms);
        double cryptoEt @unit(ms) = default(0.31ms);
        double cryptoMt @unit(ms) = default(0.003ms);
        double cryptoBM @unit(ms) = default(2.75ms);
        double cryptoMzr @unit(ms) = default(0.0002ms);
        int sizeG1 = default(128);
        int sizeGT = default(128);
        int sizeZq = default(20);
        // protocol
        int eta = default(3);            // key-extraction threshold
        int n = default(10);             // attribute vector dimension
        double reportInterval @unit(s) = default(1s);
        double reauthInterval @unit(s) = default(60s);
        double authTimeout @unit(s) = default(2s);
        double keyReqInterval @unit(s) = default(0.5s);
        int maxAuthRetries = default(3);
        // ---- one-to-one signature-based competitor parameters -----------------
        // cost of producing the authentication request on the vehicle side,
        // expressed in numbers of measured primitives. Zero for the proposed
        // scheme (its request cost is already covered by the key combination).
        int signEg1Count = default(0);
        int signBMCount = default(0);
        // authentication message size in bytes; 0 selects the native size of
        // the proposed scheme (2|G_1| + |id| + 8)
        int authMsgBytes = default(0);
}

//
// Road-side unit application: partial key extraction, relay of authentication
// traffic between vehicles and the AS, ciphertext aggregation.
//
simple RSUApp extends DemoBaseApplLayer
{
    parameters:
        @class(veins::RSUApp);
        double cryptoEg1 @unit(ms) = default(5.5ms);
        double cryptoMg1 @unit(ms) = default(0.03ms);
        double cryptoEg2 @unit(ms) = default(5.5ms);
        double cryptoMg2 @unit(ms) = default(0.03ms);
        double cryptoEt @unit(ms) = default(0.31ms);
        double cryptoMt @unit(ms) = default(0.003ms);
        double cryptoBM @unit(ms) = default(2.75ms);
        double cryptoMzr @unit(ms) = default(0.0002ms);
        int sizeG1 = default(128);
        int sizeGT = default(128);
        int sizeZq = default(20);
        double aggWindow @unit(s) = default(1s);
        double backhaulDelay @unit(s) = default(10ms);
        double helloInterval @unit(s) = default(1s);
        string aggMode = default("aggregated"); // "paper" | "aggregated" (component-wise)
    gates:
        input backendIn @directIn;
}

//
// Application server: one-to-many authentication (or one-to-one baseline),
// aggregation decryption.
//
simple ASApp
{
    parameters:
        @class(veins::ASApp);
        double cryptoEg1 @unit(ms) = default(5.5ms);
        double cryptoMg1 @unit(ms) = default(0.03ms);
        double cryptoEg2 @unit(ms) = default(5.5ms);
        double cryptoMg2 @unit(ms) = default(0.03ms);
        double cryptoEt @unit(ms) = default(0.31ms);
        double cryptoMt @unit(ms) = default(0.003ms);
        double cryptoBM @unit(ms) = default(2.75ms);
        double cryptoMzr @unit(ms) = default(0.0002ms);
        int sizeG1 = default(128);
        int sizeGT = default(128);
        int sizeZq = default(20);
        string authMode = default("o2m");       // "o2m" | "o2o"
        string decMode = default("aggregated"); // "paper" | "aggregated"
        double batchWindow @unit(s) = default(0.2s);
        double ackWindow @unit(s) = default(0.5s);
        double backhaulDelay @unit(s) = default(10ms);
        int dlRange = default(1024);            // brute-force DL result space
        int n = default(10);
        // ---- one-to-one path costs, in numbers of measured primitives --------
        // The proposed scheme's own one-to-one variant uses delta = 2E_g1 + 1BM
        // and verify = 2E_g1 + 1BM. A signature-based competitor performs no
        // AS-side delta, so o2oDelta* is set to 0 and o2oVerify* carries its
        // signature-verification cost.
        string canvasBgImage = default("");     // optional canvas background (Qtenv)
        int o2oDeltaEg1 = default(2);
        int o2oDeltaBM = default(1);
        int o2oVerifyEg1 = default(2);
        int o2oVerifyBM = default(1);
    gates:
        input directIn @directIn;
}

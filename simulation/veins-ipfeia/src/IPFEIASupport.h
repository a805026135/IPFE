#pragma once

#include "veins/veins.h"

#include "veins/base/phyLayer/PhyToMacControlInfo.h"
#include "veins/base/utils/SimpleAddress.h"
#include "veins/modules/messages/BaseFrame1609_4_m.h"

#include <iomanip>
#include <iostream>

namespace veins {

// Sender L2 address of a received WSM: Veins 5.2 carries it in the
// PhyToMacControlInfo attached by the MAC layer, not in the frame itself.
inline LAddress::L2Type senderOf(const BaseFrame1609_4* wsm)
{
    auto* ci = dynamic_cast<PhyToMacControlInfo*>(wsm->getControlInfo());
    return ci ? ci->getSourceAddress() : LAddress::L2BROADCAST();
}

// Per-primitive cryptographic operation costs, measured with jPBC on the same
// Type-A pairing parameters as the scheme implementation (see
// simulation/crypto-bench). Injected as NED parameters so that the simulation
// uses real computation times instead of instantaneous crypto.
struct CryptoCosts {
    simtime_t Eg1, Mg1, Eg2, Mg2, Et, Mt, BM, Mzr;
    int g1Bytes, gtBytes, zqBytes;

    void readParams(cModule* owner)
    {
        // NOTE: cPar converts to simtime_t through cPar::operator double(),
        // which returns the *raw* number and DROPS the declared @unit -- so
        // "5.5002ms" would become 5.5002 s. doubleValueInUnit("s") applies the
        // unit conversion and yields the correct 0.0055002 s.
        Eg1 = owner->par("cryptoEg1").doubleValueInUnit("s");
        Mg1 = owner->par("cryptoMg1").doubleValueInUnit("s");
        Eg2 = owner->par("cryptoEg2").doubleValueInUnit("s");
        Mg2 = owner->par("cryptoMg2").doubleValueInUnit("s");
        Et = owner->par("cryptoEt").doubleValueInUnit("s");
        Mt = owner->par("cryptoMt").doubleValueInUnit("s");
        BM = owner->par("cryptoBM").doubleValueInUnit("s");
        Mzr = owner->par("cryptoMzr").doubleValueInUnit("s");
        g1Bytes = owner->par("sizeG1");
        gtBytes = owner->par("sizeGT");
        zqBytes = owner->par("sizeZq");
    }

    simtime_t g1(int exps, int muls) const
    {
        return Eg1 * exps + Mg1 * muls;
    }
    simtime_t g2(int exps, int muls) const
    {
        return Eg2 * exps + Mg2 * muls;
    }
    simtime_t gt(int exps, int muls) const
    {
        return Et * exps + Mt * muls;
    }
    // brute-force discrete log over a result space of size range
    simtime_t dl(int range) const
    {
        return Et + Mt * (range / 2);
    }
};

inline void ipfeiaLogHeader()
{
    std::cout << std::fixed << std::setprecision(3);
}

} // namespace veins

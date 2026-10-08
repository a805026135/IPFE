# -*- coding: utf-8 -*-
"""Why a handful of vehicles are not authenticated at 200/500 vehicles
(reviewer M2): are they failed, or still travelling at t=300 s?"""
import glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "veins-ipfeia", "results")

for scen in ("c200_v50", "c500_v50"):
    print(f"=== {scen} ===")
    for p in sorted(glob.glob(os.path.join(RES, f"{scen}_s*_O2M_AGG.log"))):
        vehs, ok, last_t = {}, set(), {}
        with open(p, "r", errors="replace") as f:
            for line in f:
                if not line.startswith("IPFEIA_LOG,"):
                    continue
                q = line[len("IPFEIA_LOG,"):].strip().split(",")
                try:
                    if q[0] == "VEH_SUMMARY":
                        vehs[q[1]] = (int(q[2]), int(q[6]))  # auths, authed flag
                    elif q[0] == "AUTH_OK":
                        ok.add(q[1]); last_t[q[1]] = float(q[2])
                except (ValueError, IndexError):
                    continue
        un = [v for v, (a, fl) in vehs.items() if fl != 1]
        # a vehicle still in the network at the end has events close to 300 s
        late = [v for v in un if last_t.get(v, 0) > 280]
        print(f"  {os.path.basename(p)[:22]:22s} veh={len(vehs):4d} unauthed={len(un)} "
              f"(late/last>280s: {len(late)})")

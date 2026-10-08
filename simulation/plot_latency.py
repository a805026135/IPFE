"""Plot end-to-end latency scaling and speed robustness from results/summary.csv.
Outputs results/figs/latency.png with two panels:
  (a) initial-auth / re-auth / join time vs. fleet size (one-to-many, 50 km/h)
  (b) join time vs. vehicle speed (100-vehicle fleet, one-to-many)
"""
import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "veins-ipfeia", "results")


def main():
    rows = list(csv.DictReader(open(os.path.join(RES, "summary.csv"), encoding="utf-8")))

    def get(cfg, scen):
        return next(r for r in rows if r["config"] == cfg and r["scenario"] == scen)

    fleets = [20, 50, 100, 200, 500]
    scens = ["c20_v50", "c50_v50", "c100_v50", "c200_v50", "c500_v50"]
    init = [float(get("O2M_AGG", s)["initial_latency_mean_ms"]) / 1000 for s in scens]
    reau = [float(get("O2M_AGG", s)["reauth_latency_mean_ms"]) / 1000 for s in scens]
    join = [float(get("O2M_AGG", s)["join_time_mean_ms"]) / 1000 for s in scens]

    speeds = [30, 50, 80, 120]
    sj = [float(get("O2M_AGG", f"c100_v{v}")["join_time_mean_ms"]) / 1000 for v in speeds]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.6, 3.4))

    axL.plot(fleets, init, marker="o", label="initial authentication")
    axL.plot(fleets, reau, marker="s", label="re-authentication")
    axL.plot(fleets, join, marker="^", label="end-to-end join time")
    axL.set_xscale("log")
    axL.set_xticks(fleets)
    axL.set_xticklabels([str(f) for f in fleets])
    axL.minorticks_off()
    axL.set_xlabel("fleet size (vehicles)")
    axL.set_ylabel("mean latency (s)")
    axL.set_ylim(0, 7)
    axL.grid(alpha=0.3)
    axL.legend(fontsize=8)

    axR.plot(speeds, sj, marker="o")
    axR.set_xticks(speeds)
    axR.set_xlabel("nominal vehicle speed (km/h)")
    axR.set_ylabel("mean join time (s)")
    axR.set_ylim(0, 6)
    axR.grid(alpha=0.3)

    fig.tight_layout()
    out = os.path.join(RES, "figs", "latency.png")
    fig.savefig(out, dpi=150)
    print("wrote", out)


if __name__ == "__main__":
    main()

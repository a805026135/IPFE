# -*- coding: utf-8 -*-
"""Effect of excluding the demand-injection transient (first 120 s) from the
steady-state latency statistics -- needed to state a defensible warm-up in the
paper (reviewer M1)."""
import glob, os, re, statistics, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "veins-ipfeia", "results")


def load(path):
    init, reauth, join = [], [], []
    with open(path, "r", errors="replace") as f:
        for line in f:
            if not line.startswith("IPFEIA_LOG,"):
                continue
            p = line[len("IPFEIA_LOG,"):].strip().split(",")
            try:
                if p[0] == "AUTH_OK" and float(p[2]) >= 120:
                    (init if p[5] == "initial" else reauth).append(float(p[3]))
                elif p[0] == "JOIN_DONE" and float(p[2]) >= 120:
                    join.append(float(p[3]))
            except (ValueError, IndexError):
                continue
    return init, reauth, join


def all_events(path):
    init, reauth, join = [], [], []
    with open(path, "r", errors="replace") as f:
        for line in f:
            if not line.startswith("IPFEIA_LOG,"):
                continue
            p = line[len("IPFEIA_LOG,"):].strip().split(",")
            try:
                if p[0] == "AUTH_OK":
                    (init if p[5] == "initial" else reauth).append(float(p[3]))
                elif p[0] == "JOIN_DONE":
                    join.append(float(p[3]))
            except (ValueError, IndexError):
                continue
    return init, reauth, join


def mean(v):
    return statistics.mean(v) if v else float("nan")


print(f"{'scenario':10s} {'metric':12s} {'all (ms)':>10s} {'t>=120s (ms)':>13s} {'delta':>8s}")
for scen in ("c20_v50", "c50_v50", "c100_v50", "c200_v50", "c500_v50"):
    A = [[], [], []]
    B = [[], [], []]
    for p in sorted(glob.glob(os.path.join(RES, f"{scen}_s*_O2M_AGG.log"))):
        a = all_events(p); b = load(p)
        for i in range(3):
            A[i] += a[i]; B[i] += b[i]
    for i, lb in enumerate(("init", "reauth", "join")):
        print(f"{scen:10s} {lb:12s} {mean(A[i]):10.1f} {mean(B[i]):13.1f} "
              f"{mean(B[i])-mean(A[i]):+8.1f}   n {len(A[i])}->{len(B[i])}")
    print()

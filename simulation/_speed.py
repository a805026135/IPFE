# -*- coding: utf-8 -*-
"""Speed-sweep details needed for the paper's mobility paragraph."""
import glob, math, os, statistics, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "veins-ipfeia", "results")
sys.path.insert(0, os.path.join(HERE, "veins-ipfeia"))
import analyze
T95 = {2: 12.71, 3: 4.303, 4: 3.182, 5: 2.776}


def ci(v):
    v = [x for x in v if x is not None and not math.isnan(x)]
    return T95.get(len(v), 1.96) * statistics.stdev(v) / math.sqrt(len(v)) if len(v) > 1 else 0.0


def m(v):
    v = [x for x in v if x is not None and not math.isnan(x)]
    return statistics.mean(v) if v else float("nan")


print(f"{'speed':10s} {'fan-out':>16s} {'join (s)':>16s} {'init (s)':>16s} {'succ %':>8s} {'retries':>8s}")
for v in (30, 50, 80, 120):
    scen = f"c100_v{v}"
    ds = []
    for p in sorted(glob.glob(os.path.join(RES, f"{scen}_s*_O2M_AGG.log"))):
        try:
            ds.append(analyze.parse_log(p).finish())
        except Exception:
            pass
    if not ds:
        continue
    fan = [d["vehicles_per_batch"] for d in ds]
    jt = [d["join_time_mean_ms"] / 1000 for d in ds]
    it = [d["initial_latency_mean_ms"] / 1000 for d in ds]
    sr = [d["success_rate"] * 100 for d in ds]
    rt = [d["auth_fail_total"] / max(d["authed_vehicles"], 1) for d in ds]
    print(f"{v:3d} km/h   {m(fan):6.2f}+/-{ci(fan):.2f}  {m(jt):6.2f}+/-{ci(jt):.2f}  "
          f"{m(it):6.2f}+/-{ci(it):.2f}  {m(sr):7.1f}  {m(rt):8.2f}")

# -*- coding: utf-8 -*-
"""RSU-density comparison (reviewer M7): 15 / 25 / 35 RSUs at 100 and 500 vehicles."""
import glob, math, os, re, statistics, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "veins-ipfeia", "results")
sys.path.insert(0, os.path.join(HERE, "veins-ipfeia"))
import analyze

T95 = {2: 12.71, 3: 4.303, 4: 3.182, 5: 2.776}


def ci95(v):
    v = [x for x in v if x is not None and not math.isnan(x)]
    return T95.get(len(v), 1.96) * statistics.stdev(v) / math.sqrt(len(v)) if len(v) > 1 else 0.0


def m(v):
    v = [x for x in v if x is not None and not math.isnan(x)]
    return statistics.mean(v) if v else float("nan")


def load(p):
    try:
        return analyze.parse_log(p).finish()
    except Exception as exc:
        print("skip", p, exc)
        return None


print("=== RSU density: 15 / 25 / 35 (mean +/- 95% CI over the 5 seeds at 25) ===")
for scen, fleet in (("c100_v50", 100), ("c500_v50", 500)):
    # 15 and 35 are single runs, kept in dens_*.log
    for K in (15, 35):
        p = os.path.join(RES, f"dens_r{K}_{scen}.log")
        d = load(p) if os.path.exists(p) else None
        if not d:
            print(f"  {scen} r{K}: missing"); continue
        print(f"  {scen} {K:2d} RSUs  fan-out {d['vehicles_per_batch']:5.2f}  "
              f"per-bcast {d['as_auth_busy_ms']/max(d['as_batches'],1):6.2f} ms  "
              f"as/veh {d['as_auth_per_authed_ms']:6.2f} ms  "
              f"join {d['join_time_mean_ms']/1000:5.2f}s  "
              f"init {d['initial_latency_mean_ms']/1000:5.2f}s  "
              f"succ {d['success_rate']*100:5.1f}%  "
              f"rets/veh {d['auth_fail_total']/max(d['authed_vehicles'],1):5.2f}  "
              f"load {d['channel_kbps']:7.1f} kbit/s")
    # 25 RSUs = the seed pool
    ds = []
    for p in sorted(glob.glob(os.path.join(RES, f"{scen}_s*_O2M_AGG.log"))):
        d = load(p)
        if d:
            ds.append(d)
    if ds:
        fan = [d["vehicles_per_batch"] for d in ds]
        pb = [d["as_auth_busy_ms"] / d["as_batches"] for d in ds if d["as_batches"]]
        av = [d["as_auth_per_authed_ms"] for d in ds if d["as_auth_per_authed_ms"] is not None]
        jt = [d["join_time_mean_ms"] / 1000 for d in ds]
        it = [d["initial_latency_mean_ms"] / 1000 for d in ds]
        sr = [d["success_rate"] * 100 for d in ds]
        rt = [d["auth_fail_total"] / max(d["authed_vehicles"], 1) for d in ds]
        ld = [d["channel_kbps"] for d in ds]
        print(f"  {scen} 25 RSUs  fan-out {m(fan):5.2f}+/-{ci95(fan):.2f}  "
              f"per-bcast {m(pb):6.2f}+/-{ci95(pb):.2f} ms  "
              f"as/veh {m(av):6.2f}+/-{ci95(av):.2f} ms  "
              f"join {m(jt):5.2f}+/-{ci95(jt):.2f}s  "
              f"init {m(it):5.2f}+/-{ci95(it):.2f}s  "
              f"succ {m(sr):5.1f}%  rets/veh {m(rt):5.2f}  "
              f"load {m(ld):7.1f} kbit/s")
    print()

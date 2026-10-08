# -*- coding: utf-8 -*-
"""R3 robustness check: urban empirical path-loss exponent (alpha = 3.0).

Compares the main result set (results/, alpha = 2.0) with the robustness batch
(results_alpha3/, alpha = 3.0) at 100 and 500 vehicles, five seeds each.
Prints mean +/- 95% CI for the quantities the paper reports.
"""
import glob
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "veins-ipfeia"))
import analyze  # noqa: E402
from analyze_ci import ci95  # noqa: E402


def collect(folder, fleet):
    out = []
    for path in sorted(glob.glob(os.path.join(folder, "*.log"))):
        m = analyze.parse_log(path)
        if m.config != "O2M_AGG":
            continue
        if m.fleet() != fleet or not re.search(r"_s\d+$", m.scenario):
            continue
        d = m.finish()
        if d["vehicles"]:
            out.append(d)
    return out


def ms(ds, key, scale=1.0, digits=2):
    vals = [d[key] / scale for d in ds if d.get(key) is not None]
    vals = [v for v in vals if v == v]
    if not vals:
        return "n/a"
    return f"{statistics.mean(vals):.{digits}f} +/- {ci95(vals):.{digits}f}"


def line(tag, ds):
    if not ds:
        return f"  {tag:7s} no data"
    sr = [d["success_rate"] * 100 for d in ds]
    return (f"  {tag:7s} n={len(ds)}  success={statistics.mean(sr):5.1f}%  "
            f"join={ms(ds, 'join_time_mean_ms', 1000.0)}s  "
            f"init={ms(ds, 'initial_latency_mean_ms', 1000.0)}s  "
            f"as/veh={ms(ds, 'as_auth_per_authed_ms')}ms  "
            f"veh/batch={ms(ds, 'vehicles_per_batch')}  "
            f"chan={ms(ds, 'channel_kbps', 1.0)}kbps")


def main():
    print("R3 robustness: path-loss exponent 2.0 (main) vs 3.0 (urban empirical)")
    for fleet in (100, 500):
        a2 = collect(os.path.join(HERE, "veins-ipfeia", "results"), fleet)
        a3 = collect(os.path.join(HERE, "veins-ipfeia", "results_alpha3"), fleet)
        print(f"\n--- fleet = {fleet} ---")
        print(line("alpha2", a2))
        print(line("alpha3", a3))


if __name__ == "__main__":
    main()

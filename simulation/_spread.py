# -*- coding: utf-8 -*-
"""Per-seed spread table for the paper's repeated-run claim (reviewer M1)."""
import glob, os, re, sys, statistics
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "veins-ipfeia", "results")
sys.path.insert(0, os.path.join(HERE, "veins-ipfeia"))
import analyze

rows = {}
for p in sorted(glob.glob(os.path.join(RES, "*.log"))):
    try:
        d = analyze.parse_log(p).finish()
    except Exception:
        continue
    if not re.search(r"_s\d+$", d["scenario"]):
        continue
    base = d["scenario"].rsplit("_s", 1)[0]
    rows.setdefault((d["config"], base), []).append(d)

print(f"{'config':10s} {'scenario':10s} {'n':>2s}  {'as/veh min..max':>22s}  "
      f"{'join min..max (s)':>20s}  {'veh/bcast':>16s}")
for (cfg, base), ds in sorted(rows.items()):
    pv = [d["as_auth_per_authed_ms"] for d in ds if d.get("as_auth_per_authed_ms") is not None]
    jt = [d["join_time_mean_ms"]/1000 for d in ds]
    vb = [d["vehicles_per_batch"] for d in ds if d.get("vehicles_per_batch") is not None]
    pv = [v for v in pv if v == v]
    print(f"{cfg:10s} {base:10s} {len(ds):2d}  "
          f"{min(pv):8.2f}..{max(pv):8.2f}   {min(jt):7.2f}..{max(jt):7.2f}   "
          f"{min(vb):6.2f}..{max(vb):6.2f}")

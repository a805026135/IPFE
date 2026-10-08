"""Render a simulation scenario from its generated files.

Draws the road network of scenarios/<name>/<name>.net.xml, the RSU deployment
from scenarios/rsu_positions.ini and (optionally) the vehicle positions of a
SUMO floating-car-data export.

Usage:
    python render_scenario.py <scenario_name> <out.png> "<title>" [fcd.xml t_snap]

Example:
    sumo -c scenarios/c100_v50/c100_v50.sumo.cfg --fcd-output fcd.xml --end 160
    python render_scenario.py c100_v50 out.png "SNNU Yanta campus" fcd.xml 150
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = os.path.join(HERE, "veins-ipfeia", "scenarios")

name = sys.argv[1]
out_png = sys.argv[2]
title = sys.argv[3] if len(sys.argv) > 3 else ""
fcd_path = sys.argv[4] if len(sys.argv) > 4 else None
t_snap = float(sys.argv[5]) if len(sys.argv) > 5 else None

sc = os.path.join(SCEN, name)

# ------------------------------------------------------------------ road net
root = ET.parse(os.path.join(sc, f"{name}.net.xml")).getroot()
segs = []
for edge in root.findall("edge"):
    if edge.get("function") == "internal":
        continue
    for lane in edge.findall("lane"):
        shape = lane.get("shape")
        if shape:
            segs.append([tuple(map(float, p.split(","))) for p in shape.split()])

# ------------------------------------------------------------------ RSU layout
rsus = {}
for line in open(os.path.join(SCEN, "rsu_positions.ini"), encoding="utf-8"):
    m = re.match(r"\*\.rsu\[(\d+)\]\.mobility\.([xyz]) = ([\d.]+)", line.strip())
    if m:
        rsus.setdefault(int(m.group(1)), {})[m.group(2)] = float(m.group(3))
rsu_xy = [(v["x"], v["y"]) for _, v in sorted(rsus.items())]

# ------------------------------------------------------------------- vehicles
veh = []
if fcd_path and t_snap is not None:
    snap = None
    for ts in ET.parse(fcd_path).getroot().findall("timestep"):
        if float(ts.get("time")) <= t_snap:
            snap = ts
        else:
            break
    if snap is not None:
        veh = [(float(v.get("x")), float(v.get("y"))) for v in snap.findall("vehicle")]

# -------------------------------------------------------------------- drawing
fig, ax = plt.subplots(figsize=(6.4, 5.8))
for pts in segs:
    ax.plot([p[0] for p in pts], [p[1] for p in pts],
            color="0.62", linewidth=1.1, solid_capstyle="round", zorder=1)

for vx, vy in veh:
    if rsu_xy:
        rx, ry = min(rsu_xy, key=lambda r: (r[0] - vx) ** 2 + (r[1] - vy) ** 2)
        ax.plot([vx, rx], [vy, ry], color="tab:blue", linewidth=0.25, alpha=0.3, zorder=2)

if veh:
    ax.scatter([p[0] for p in veh], [p[1] for p in veh], s=14, marker="o",
               facecolor="tab:blue", edgecolor="white", linewidth=0.4, zorder=4,
               label=f"vehicles ({len(veh)})")
if rsu_xy:
    ax.scatter([p[0] for p in rsu_xy], [p[1] for p in rsu_xy], s=64, marker="s",
               facecolor="tab:red", edgecolor="black", linewidth=0.5, zorder=5,
               label=f"RSUs ({len(rsu_xy)})")

xs = [p[0] for s in segs for p in s]
ys = [p[1] for s in segs for p in s]
ax.set_xlim(min(xs) - 40, max(xs) + 40)
ax.set_ylim(min(ys) - 40, max(ys) + 40)
ax.set_aspect("equal")
ax.set_xlabel("x (m)")
ax.set_ylabel("y (m)")
if title:
    ax.set_title(title, fontsize=10)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=2, fontsize=9,
          frameon=False)
ax.grid(alpha=0.12)
fig.tight_layout()
fig.savefig(out_png, dpi=200)
print(f"wrote {out_png}  (edges={len(segs)}, RSUs={len(rsu_xy)}, vehicles={len(veh)})")

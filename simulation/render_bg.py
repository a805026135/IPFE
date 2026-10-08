"""Render a map-style background image of the real SUMO network:
roads (coloured by OSM type, dark casing) + building footprints.
1 image pixel = 1 metre; the image covers playground + margins.
Used as the Qtenv canvas background via a cImageFigure ("campus_bg").
"""
import os
import sys
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Polygon

SC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veins-ipfeia", "scenarios")
MARGIN = 25  # must match veins' TraCIScenarioManager margin (default 25)
DPI = 200
PT_PER_PX = 72.0 / DPI

TYPE_COLORS = {
    "highway.primary": "#d2849a", "highway.primary_link": "#d2849a",
    "highway.secondary": "#e8b26e", "highway.secondary_link": "#e8b26e",
    "highway.tertiary": "#e6e89a", "highway.tertiary_link": "#e6e89a",
    "highway.unclassified": "#ffffff", "highway.residential": "#f7f7f7",
    "highway.service": "#d0d0d0", "highway.living_street": "#ededed",
}
# road width in metres (exaggerated ~3x so roads stay visible when zoomed out)
TYPE_WIDTH_M = {
    "highway.primary": 24, "highway.primary_link": 20,
    "highway.secondary": 20, "highway.secondary_link": 16,
    "highway.tertiary": 16, "highway.tertiary_link": 14,
    "highway.unclassified": 12, "highway.residential": 12,
    "highway.service": 8, "highway.living_street": 10,
}


def main():
    net_path, out_path = sys.argv[1], sys.argv[2]
    root = ET.parse(net_path).getroot()
    loc = root.find("location")
    minx, miny, maxx, maxy = [float(v) for v in loc.get("convBoundary").split(",")]
    W, H = maxx - minx, maxy - miny

    fig = plt.figure(figsize=((W + 2 * MARGIN) / 100.0, (H + 2 * MARGIN) / 100.0), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    # image pixel (0,0) = canvas (0,0) top-left; canvas y is DOWN, so invert:
    ax.set_xlim(minx - MARGIN, maxx + MARGIN)
    ax.set_ylim(maxy + MARGIN, miny - MARGIN)
    ax.set_facecolor("#f2efe9")

    fill_segs, fill_colors, fill_w_pt = [], [], []
    case_segs, case_w_pt = [], []
    for e in root.findall("edge"):
        if e.get("function") == "internal":
            continue
        t = e.get("type", "")
        color = TYPE_COLORS.get(t, "#e0e0e0")
        w_m = TYPE_WIDTH_M.get(t, 10)
        lanes = e.findall("lane")
        lane_count = max(1, len(lanes))
        w_m = min(w_m * lane_count, 40)
        for lane in lanes:
            shp = lane.get("shape")
            if not shp:
                continue
            pts = [tuple(map(float, p.split(","))) for p in shp.split()]
            fill_segs.append(pts)
            fill_colors.append(color)
            fill_w_pt.append(w_m * PT_PER_PX)
            case_segs.append(pts)
            case_w_pt.append((w_m + 6) * PT_PER_PX)
    print("lane segments:", len(fill_segs))
    ax.add_collection(LineCollection(case_segs, colors="#9a9a9a",
                                     linewidths=case_w_pt, capstyle="round", zorder=1.5))
    ax.add_collection(LineCollection(fill_segs, colors=fill_colors,
                                     linewidths=fill_w_pt, capstyle="round", zorder=2))

    # building footprints
    polys = []
    poly_path = os.path.join(os.path.dirname(net_path),
                             os.path.basename(net_path).replace(".net.xml", ".poly.xml"))
    ptree = ET.parse(poly_path)
    for p in ptree.getroot().findall("poly"):
        if p.get("type") != "building" or not p.get("shape"):
            continue
        pts = [tuple(map(float, c.split(","))) for c in p.get("shape").split()]
        polys.append(Polygon(pts, closed=True))
    print("buildings:", len(polys))
    if polys:
        ax.add_collection(PatchCollection(polys, facecolor="#c8bcb0",
                                          edgecolor="#9a8f84", linewidths=1.2, zorder=3))

    ax.axis("off")
    fig.savefig(out_path, dpi=DPI)
    print("saved", out_path, "canvas %.0fx%.0f m" % (W, H))


if __name__ == "__main__":
    main()

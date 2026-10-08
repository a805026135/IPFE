#!/usr/bin/env python
"""Generate the SUMO grid scenario, vehicle demand and RSU deployment
for the IPFE-IA Veins/OMNeT++ simulation.

Outputs (under --out):
  grid.net.xml                  shared Manhattan grid (10x10 junctions, 250m blocks,
                                2 lanes per edge, 120 km/h lane speed limit, TLS)
  <name>.rou.xml                demand with an exact vehicle count and target speed
  <name>.sumo.cfg               SUMO run config (300 s)
  rsu_positions.ini             Veins NED fragment: playground size + RSU x/y/z
                                (y-axis flipped to Veins coordinates)
  <name>/ipfeia.launchd.xml     Veins launchd config per scenario (files copied)

Run with the venv python (has sumolib):
  ..\\venv\\Scripts\\python.exe generate_scenario.py
"""
import argparse
import os
import random
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))

def _dep(*rel):
    """Third-party dependencies may sit inside this directory or next to it
    (see README.md); resolve to whichever exists."""
    for base in (os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")):
        p = os.path.join(base, *rel)
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.abspath(os.path.join(HERE, "..", *rel))

IS_WIN = sys.platform.startswith("win")
BIN_SUFFIX = ".exe" if IS_WIN else ""
_VENV = _dep("venv")
SUMO_BIN = os.path.join(_VENV, "Scripts")
VEINS_PROJ = os.path.join(HERE, "..", "veins-ipfeia")

MAX_SPEED = 33.33  # m/s lane speed limit (120 km/h), speed variants via vType speedFactor


def run_sumo_tool(name, *args):
    exe = os.path.join(SUMO_BIN, name + BIN_SUFFIX)
    cmd = [exe] + [str(a) for a in args]
    print("  $ " + " ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True)


def build_grid(out_dir, grid_number, grid_length):
    raw = os.path.join(out_dir, "grid_raw.net.xml")
    tls = os.path.join(out_dir, "grid_tls.net.xml")
    final = os.path.join(out_dir, "grid.net.xml")
    run_sumo_tool("netgenerate", "--grid", "--grid.number", grid_number,
                  "--grid.length", grid_length, "--default.lanenumber", "2",
                  "--no-turnarounds", "-o", raw)
    run_sumo_tool("netconvert", "-s", raw, "--tls.guess", "--no-turnarounds", "-o", tls)
    # raise lane speed limit so that the speed variants are not capped by the road
    tree = ET.parse(tls)
    for lane in tree.getroot().iter("lane"):
        lane.set("speed", str(MAX_SPEED))
    tree.write(final, encoding="UTF-8", xml_declaration=True)
    os.remove(raw)
    os.remove(tls)
    return final


def pick_rsus(net, step):
    """Every `step`-th junction along each axis (interior grid)."""
    nodes = [n for n in net.getNodes()]
    xs = sorted({round(n.getCoord()[0]) for n in nodes})
    ys = sorted({round(n.getCoord()[1]) for n in nodes})
    xs_sel = xs[1::step]
    ys_sel = ys[1::step]
    rsus = []
    for x in xs_sel:
        for y in ys_sel:
            rsus.append((x, y))
    return rsus


def make_demand(net, count, speed_kmh, seed, duration, depart_until):
    rng = random.Random(seed)
    edges = [e for e in net.getEdges() if e.getFunction() != "internal"]
    vehicles = []
    tries = 0
    while len(vehicles) < count and tries < count * 60:
        tries += 1
        fe = rng.choice(edges)
        te = rng.choice(edges)
        if fe.getID() == te.getID():
            continue
        route, cost = net.getShortestPath(fe, te)
        if not route or len(route) < 3:
            continue
        depart = round(rng.uniform(1.0, depart_until), 1)
        vehicles.append((depart, [e.getID() for e in route]))
    vehicles.sort(key=lambda v: v[0])
    speed_factor = (speed_kmh / 3.6) / MAX_SPEED
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<routes>",
             '  <vType id="car" vClass="passenger" length="5" minGap="2.5" accel="2.6"'
             ' decel="4.5" sigma="0.5" maxSpeed="%.2f" speedFactor="%.4f" speedDev="0.1"/>'
             % (MAX_SPEED, speed_factor)]
    for i, (depart, route) in enumerate(vehicles):
        lines.append('  <vehicle id="veh%d" type="car" depart="%.1f" departPos="random"'
                     ' departSpeed="desired" departLane="best">' % (i, depart))
        lines.append('    <route edges="%s"/>' % " ".join(route))
        lines.append("  </vehicle>")
    lines.append("</routes>")
    return "\n".join(lines) + "\n", len(vehicles)


def write_cfg(path, name, duration):
    with open(path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                "<configuration>\n"
                "  <input>\n"
                '    <net-file value="grid.net.xml"/>\n'
                '    <route-files value="%s.rou.xml"/>\n'
                "  </input>\n"
                "  <time>\n"
                '    <begin value="0"/>\n'
                '    <end value="%d"/>\n'
                "  </time>\n"
                "  <processing>\n"
                '    <time-to-teleport value="60"/>\n'
                "  </processing>\n"
                "</configuration>\n" % (name, duration))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid-number", type=int, default=10)
    ap.add_argument("--grid-length", type=float, default=250.0)
    ap.add_argument("--duration", type=int, default=300)
    ap.add_argument("--counts", default="20,50,100,200,500")
    ap.add_argument("--speeds", default="30,50,80,120")
    ap.add_argument("--count-sweep-speed", type=int, default=50)
    ap.add_argument("--speed-sweep-count", type=int, default=100)
    ap.add_argument("--rsu-step", type=int, default=2)
    ap.add_argument("--depart-until", type=float, default=120.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=os.path.join(HERE, "scenarios"))
    args = ap.parse_args()

    import sumolib

    os.makedirs(args.out, exist_ok=True)
    print("building grid network ...")
    net_path = build_grid(args.out, args.grid_number, args.grid_length)
    net = sumolib.net.readNet(net_path)
    x1, y1, x2, y2 = net.getBoundary()
    size_x = int((x2 - x1 + 99) // 50 * 50)
    size_y = int((y2 - y1 + 99) // 50 * 50)

    rsus = pick_rsus(net, args.rsu_step)
    print("grid: %.0fm x %.0fm, %d edges, %d junctions, %d RSUs"
          % (x2 - x1, y2 - y1, len(net.getEdges()), len(net.getNodes()), len(rsus)))

    with open(os.path.join(args.out, "rsu_positions.ini"), "w") as f:
        f.write("# auto-generated by generate_scenario.py -- do not edit\n")
        f.write("*.playgroundSizeX = %dm\n" % size_x)
        f.write("*.playgroundSizeY = %dm\n" % size_y)
        f.write("*.playgroundSizeZ = 50m\n")
        f.write("*.numRsus = %d\n" % len(rsus))
        for i, (x, y) in enumerate(rsus):
            f.write("*.rsu[%d].mobility.x = %d\n" % (i, x))
            f.write("*.rsu[%d].mobility.y = %d\n" % (i, size_y - y))  # SUMO y-down -> Veins y-up
            f.write("*.rsu[%d].mobility.z = 3\n" % i)
    # reference copy with SUMO coordinates for analysis
    with open(os.path.join(args.out, "rsu_positions_sumo.txt"), "w") as f:
        for i, (x, y) in enumerate(rsus):
            f.write("%d %d %d\n" % (i, x, y))

    scenarios = []
    for c in [int(v) for v in args.counts.split(",")]:
        scenarios.append((c, args.count_sweep_speed))
    for s in [int(v) for v in args.speeds.split(",")]:
        if (args.speed_sweep_count, s) not in scenarios:
            scenarios.append((args.speed_sweep_count, s))

    for (count, speed) in scenarios:
        name = "c%d_v%d" % (count, speed)
        rou, n_veh = make_demand(net, count, speed, args.seed + count * 1000 + speed,
                                 args.duration, args.depart_until)
        rou_path = os.path.join(args.out, name + ".rou.xml")
        with open(rou_path, "w") as f:
            f.write(rou)
        write_cfg(os.path.join(args.out, name + ".sumo.cfg"), name, args.duration)
        scen_dir = os.path.join(args.out, name)
        os.makedirs(scen_dir, exist_ok=True)
        shutil.copy(net_path, os.path.join(scen_dir, "grid.net.xml"))
        shutil.copy(rou_path, os.path.join(scen_dir, name + ".rou.xml"))
        shutil.copy(os.path.join(args.out, name + ".sumo.cfg"), os.path.join(scen_dir, name + ".sumo.cfg"))
        with open(os.path.join(scen_dir, "ipfeia.launchd.xml"), "w") as f:
            f.write('<launch>\n'
                    '    <copy file="grid.net.xml" />\n'
                    '    <copy file="%s.rou.xml" />\n'
                    '    <copy file="%s.sumo.cfg" type="config" />\n'
                    '</launch>\n' % (name, name))
        print("scenario %s: %d/%d vehicles, %d km/h" % (name, n_veh, count, speed))

    # mirror scenario dirs + rsu fragment into the Veins project
    dst = os.path.join(VEINS_PROJ, "scenarios")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(args.out, dst,
                    ignore=shutil.ignore_patterns("grid_raw.net.xml", "grid_tls.net.xml"))
    print("done. scenarios in %s (mirrored to %s)" % (args.out, dst))


if __name__ == "__main__":
    main()

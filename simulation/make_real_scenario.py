"""Turn a real OpenStreetMap extract into a Veins/SUMO scenario.

Usage
-----
    python make_real_scenario.py <file.osm> <scenario_name> \
           [--bbox W,S,E,N] [--fleet 100] [--rsus 25] [--end 300]

Steps
-----
1. clip the OSM to --bbox (the Overpass recursion otherwise drags in the far
   ends of long roads and the network extent explodes);
2. netconvert          -> scenarios/<name>/<name>.net.xml  (drivable roads only)
3. polyconvert         -> scenarios/<name>/<name>.poly.xml (buildings/background)
4. randomTrips.py      -> scenarios/<name>/<name>.rou.xml  (vehicle demand)
5. writes <name>.sumo.cfg and ipfeia.launchd.xml, and regenerates
   scenarios/rsu_positions.ini (playground = net extent, RSUs spread over the
   junctions on a grid rule).

The .osm itself must be downloaded by hand from https://www.openstreetmap.org
(select the area -> Export).  For the Shaanxi Normal University Yanta campus:
    --bbox 108.9390,34.1980,108.9610,34.2145      (centre 34.2046 N, 108.9525 E)
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "veins-ipfeia")
SCEN = os.path.join(PROJ, "scenarios")

def _dep(*rel):
    """Third-party dependencies may sit inside this directory or next to it
    (see README.md); resolve to whichever exists."""
    for base in (HERE, os.path.dirname(HERE)):
        p = os.path.join(base, *rel)
        if os.path.exists(p):
            return p
    return os.path.join(HERE, *rel)

_VENV = _dep("venv")
BIN = os.path.join(_VENV, "Scripts")
PY = os.path.join(BIN, "python.exe")
SUMO_TOOLS = os.path.join(_VENV, "Lib", "site-packages", "sumo", "tools")
TYPEMAP = os.path.join(_VENV, "Lib", "site-packages", "sumo", "data",
                       "typemap", "osmPolyconvert.typ.xml")
NETCONVERT = os.path.join(BIN, "netconvert.exe")
SUMO = os.path.join(BIN, "sumo.exe")
POLYCONVERT = os.path.join(BIN, "polyconvert.exe")


def run(cmd):
    print("+ " + " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True)


def clip_osm(src, dst, west, south, east, north):
    root = ET.parse(src).getroot()
    nodes = {n.get("id"): n for n in root.findall("node")}
    keep_ways, used = [], set()
    for w in root.findall("way"):
        refs = [nd.get("ref") for nd in w.findall("nd")]
        if not refs:
            continue
        ok = True
        for r in refs:
            n = nodes.get(r)
            if n is None:
                ok = False
                break
            la, lo = float(n.get("lat")), float(n.get("lon"))
            if not (south <= la <= north and west <= lo <= east):
                ok = False
                break
        if ok:
            keep_ways.append(w)
            used.update(refs)
    out = ET.Element("osm", {"version": "0.6", "generator": "make_real_scenario.py"})
    for i in sorted(used, key=int):
        out.append(nodes[i])
    for w in keep_ways:
        out.append(w)
    ET.ElementTree(out).write(dst, encoding="utf-8", xml_declaration=True)
    print(f"  clipped: {len(nodes)} nodes -> {len(used)}, "
          f"{len(root.findall('way'))} ways -> {len(keep_ways)}")


def count_vehicles(rou_path):
    """Number of vehicle/trip/flow entries in a route file."""
    txt = open(rou_path, encoding="utf-8").read()
    return txt.count("<vehicle ") + txt.count("<trip ") + txt.count("<flow ")


def net_extent(net_path):
    loc = ET.parse(net_path).getroot().find("location")
    return tuple(float(v) for v in loc.get("convBoundary").split(","))


def junctions_on_network(net_path):
    return [(float(j.get("x")), float(j.get("y")))
            for j in ET.parse(net_path).getroot().findall("junction")
            if j.get("type") != "internal"]


def pick_rsus(points, k, minx, miny, maxx, maxy):
    """One RSU per cell of a grid covering the network, nearest junction to each
    cell centre; used to spread the infrastructure over the whole area."""
    if not points:
        return []
    nx = max(1, int(round((k * (maxx - minx) / max(1e-9, maxy - miny)) ** 0.5)))
    ny = max(1, (k + nx - 1) // nx)
    chosen = []
    for j in range(ny):
        for i in range(nx):
            cx = minx + (i + 0.5) * (maxx - minx) / nx
            cy = miny + (j + 0.5) * (maxy - miny) / ny
            best = min(points, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
            if best not in chosen:
                chosen.append(best)
    cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    for p in sorted(points, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2):
        if len(chosen) >= k:
            break
        if p not in chosen:
            chosen.append(p)
    return chosen[:k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("osm")
    ap.add_argument("name")
    ap.add_argument("--bbox", default="108.9390,34.1980,108.9610,34.2145",
                    help="west,south,east,north of the area to keep")
    ap.add_argument("--fleet", type=int, default=100)
    ap.add_argument("--rsus", type=int, default=25)
    ap.add_argument("--end", type=int, default=300)
    a = ap.parse_args()

    osm = os.path.abspath(a.osm)
    if not os.path.isfile(osm):
        sys.exit(f"OSM file not found: {osm}")
    west, south, east, north = (float(v) for v in a.bbox.split(","))

    out = os.path.join(SCEN, a.name)
    os.makedirs(out, exist_ok=True)
    net = os.path.join(out, a.name + ".net.xml")
    poly = os.path.join(out, a.name + ".poly.xml")
    rou = os.path.join(out, a.name + ".rou.xml")
    clipped = os.path.join(out, a.name + ".osm")

    clip_osm(osm, clipped, west, south, east, north)

    base = ["--osm-files", clipped, "--geometry.remove", "--roundabouts.guess",
            "--junctions.join", "--tls.guess-signals", "--tls.discard-simple",
            "--tls.join", "--no-turnarounds",
            "--keep-edges.by-vclass", "passenger", "--remove-edges.isolated"]

    # netconvert normalises the projected coordinates so that the network starts
    # at (0,0) (the projection offset is kept in <location netOffset>), so a
    # single pass is enough
    run([NETCONVERT] + base + ["-o", net])

    run([POLYCONVERT, "--net-file", net, "--osm-files", clipped,
         "--type-file", TYPEMAP, "--ignore-errors", "-o", poly])

    # Vehicle demand: keep the convention of the grid scenarios -- the scenario
    # contains exactly `fleet` vehicles, departing over the first `window`
    # seconds.  Two properties are calibrated on the real network:
    #   1. the insertion period so that the scenario holds exactly `fleet`
    #      vehicles (randomTrips cannot always route every trip it draws);
    #   2. the minimum trip distance, so that the mean trip duration -- and
    #      with it the mean number of vehicles simultaneously in the network --
    #      matches the original grid scenario (~56% of the fleet still running
    #      at the end, mean duration ~175 s).
    window = min(a.end, 120)
    m = re.search(r"_v(\d+)", a.name)
    speed_kmh = int(m.group(1)) if m else 50
    speed_factor = speed_kmh / 120.0  # vType maxSpeed is 33.33 m/s = 120 km/h
    vtype = ('<vType id="car" vClass="passenger" length="5" minGap="2.5" '
             'accel="2.6" decel="4.5" sigma="0.5" maxSpeed="33.33" '
             f'speedFactor="{speed_factor:.4f}" speedDev="0.1"/>')

    def gen(min_distance, period):
        run([PY, os.path.join(SUMO_TOOLS, "randomTrips.py"), "-n", net, "-r", rou,
             "-b", "0", "-e", str(window), "-p", f"{period:.4f}",
             "--min-distance", str(min_distance), "--seed", "42"])
        txt = open(rou, encoding="utf-8").read()
        if "<vType " in txt:
            txt = re.sub(r"<vType [^>]*/>", vtype, txt, count=1)
        else:
            txt = re.sub(r"(<routes[^>]*>)",
                         lambda m: m.group(1) + "\n  " + vtype, txt, count=1)
        # randomTrips writes <vehicle> without a type attribute -- bind every
        # vehicle to the calibrated vType, otherwise speedFactor is ignored
        txt = txt.replace("<vehicle ", '<vehicle type="car" ')
        open(rou, "w", encoding="utf-8").write(txt)
        return count_vehicles(rou)

    def calibrate_period(min_distance):
        period = max(0.02, 0.18 * window / max(1, a.fleet))
        best = None
        for _ in range(10):
            n = gen(min_distance, period)
            print(f"  calibration: md={min_distance} period={period:.4f} -> {n} vehicles (target {a.fleet})")
            if best is None or abs(n - a.fleet) < abs(best[1] - a.fleet):
                best = (period, n, open(rou, encoding="utf-8").read())
            if abs(n - a.fleet) <= max(2, 0.03 * a.fleet):
                break
            period = max(0.002, period * (n / a.fleet if n else 0.5))
        open(rou, "w", encoding="utf-8").write(best[2])
        return best[0]

    def measure_concurrency():
        """End-of-sim running count and mean trip duration from SUMO statistics."""
        p = subprocess.run([SUMO, "-n", net, "-r", rou, "-e", str(a.end),
                            "--no-step-log", "--duration-log.statistics"],
                           capture_output=True, text=True, timeout=600)
        running = duration = None
        for line in p.stdout.splitlines():
            t = line.strip()
            if t.startswith("Running:"):
                running = float(t.split()[1].rstrip("s"))
            elif t.startswith("Duration:"):
                duration = float(t.split()[1].rstrip("s"))
        return running, duration

    target_conc = round(0.56 * a.fleet)
    best = None
    for min_distance in (800, 1300, 1800):
        calibrate_period(min_distance)
        running, duration = measure_concurrency()
        score = abs((running or 0) - target_conc)
        print(f"  md={min_distance}: running={running} duration={duration}s "
              f"(target running ~{target_conc})")
        if best is None or score < best[0]:
            best = (score, min_distance, open(rou, encoding="utf-8").read())
        if running and abs(running - target_conc) <= max(3, 0.15 * target_conc):
            break
    open(rou, "w", encoding="utf-8").write(best[2])

    with open(os.path.join(out, a.name + ".sumo.cfg"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<configuration>\n'
                "  <input>\n"
                f'    <net-file value="{a.name}.net.xml"/>\n'
                f'    <route-files value="{a.name}.rou.xml"/>\n'
                "  </input>\n  <time>\n    <begin value=\"0\"/>\n"
                f'    <end value="{a.end}"/>\n    <step-length value="0.1"/>\n'
                "  </time>\n  <processing>\n    <time-to-teleport value=\"60\"/>\n"
                "  </processing>\n</configuration>\n")

    with open(os.path.join(out, "ipfeia.launchd.xml"), "w", encoding="utf-8") as f:
        f.write("<launch>\n"
                f'    <basedir path="scenarios/{a.name}" />\n'
                f'    <copy file="{a.name}.net.xml" />\n'
                f'    <copy file="{a.name}.rou.xml" />\n'
                f'    <copy file="{a.name}.sumo.cfg" type="config" />\n'
                "</launch>\n")

    maxx, maxy = net_extent(net)[2:]
    MARGIN = 25  # must match veins' TraCIScenarioManager margin (default 25)
    rsus = pick_rsus(junctions_on_network(net), a.rsus, 0.0, 0.0, maxx, maxy)
    with open(os.path.join(SCEN, "rsu_positions.ini"), "w", encoding="utf-8") as f:
        f.write("# auto-generated by make_real_scenario.py -- do not edit\n")
        f.write(f"*.playgroundSizeX = {int(maxx) + 2 * MARGIN}m\n")
        f.write(f"*.playgroundSizeY = {int(maxy) + 2 * MARGIN}m\n")
        f.write("*.playgroundSizeZ = 50m\n")
        f.write(f"*.numRsus = {len(rsus)}\n")
        for i, (x, y) in enumerate(rsus):
            f.write(f"*.rsu[{i}].mobility.x = {x + MARGIN:.1f}\n")
            # y is flipped: veins maps SUMO (x, y) -> (x, net_height - y + margin)
            f.write(f"*.rsu[{i}].mobility.y = {maxy - y + MARGIN:.1f}\n")
            f.write(f"*.rsu[{i}].mobility.z = 3\n")

    print(f"\nscenario '{a.name}': {int(maxx)} x {int(maxy)} m, "
          f"{len(rsus)} RSUs -> {out}")
    print(f"next: ./run_sim.sh O2M_AGG {a.name}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Create RSU-density variants: rsu_positions_r<k>.ini + omnetpp_r<k>.ini.

Reuses the grid-covering placement of make_real_scenario.py, so the k RSUs are
chosen from the network junctions with the same rule as the 25-RSU baseline.
"""
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "veins-ipfeia")
SCEN = os.path.join(PROJ, "scenarios")
MARGIN = 25

spec = importlib.util.spec_from_file_location(
    "mrs", os.path.join(HERE, "make_real_scenario.py"))
mrs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mrs)


def build(k, net_scen="c100_v50"):
    net = os.path.join(SCEN, net_scen, f"{net_scen}.net.xml")
    maxx, maxy = mrs.net_extent(net)[2:]
    rsus = mrs.pick_rsus(mrs.junctions_on_network(net), k, 0.0, 0.0, maxx, maxy)
    with io.open(os.path.join(SCEN, f"rsu_positions_r{k}.ini"), "w", encoding="utf-8") as f:
        f.write(f"# auto-generated: {k}-RSU density variant\n")
        f.write(f"*.playgroundSizeX = {int(maxx) + 2 * MARGIN}m\n")
        f.write(f"*.playgroundSizeY = {int(maxy) + 2 * MARGIN}m\n")
        f.write("*.playgroundSizeZ = 50m\n")
        f.write(f"*.numRsus = {len(rsus)}\n")
        for i, (x, y) in enumerate(rsus):
            f.write(f"*.rsu[{i}].mobility.x = {x + MARGIN:.1f}\n")
            f.write(f"*.rsu[{i}].mobility.y = {maxy - y + MARGIN:.1f}\n")
            f.write(f"*.rsu[{i}].mobility.z = 3\n")
    ini = io.open(os.path.join(PROJ, "omnetpp.ini"), encoding="utf-8").read()
    ini = ini.replace("include scenarios/rsu_positions.ini",
                      f"include scenarios/rsu_positions_r{k}.ini")
    with io.open(os.path.join(PROJ, f"omnetpp_r{k}.ini"), "w", encoding="utf-8") as f:
        f.write(ini)
    print(f"r{k}: {len(rsus)} RSUs -> rsu_positions_r{k}.ini + omnetpp_r{k}.ini",
          flush=True)


if __name__ == "__main__":
    for k in [int(a) for a in sys.argv[1:]] or [15, 35]:
        build(k)

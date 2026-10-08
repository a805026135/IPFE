# -*- coding: utf-8 -*-
"""Create seed variants of every scenario (same parameters, new demand seed).

For each <scenario> and seed s it creates scenarios/<scenario>_s<s>/ holding
the same network but a route file regenerated with the given seed, plus the
matching launchd XML.  Used for the repeated-runs (confidence-interval) study.
"""
import io
import os
import re
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = os.path.join(HERE, "veins-ipfeia", "scenarios")


def _dep(*rel):
    """Third-party dependencies may sit inside this directory or next to it
    (see README.md); resolve to whichever exists."""
    for base in (HERE, os.path.dirname(HERE)):
        p = os.path.join(base, *rel)
        if os.path.exists(p):
            return p
    return os.path.join(HERE, *rel)

_VENV = _dep("venv")
PY = os.path.join(_VENV, "Scripts", "python.exe")
TOOLS = os.path.join(_VENV, "Lib", "site-packages", "sumo", "tools")
BASE = ["c20_v50", "c50_v50", "c100_v50", "c200_v50", "c500_v50",
        "c100_v30", "c100_v80", "c100_v120"]
SEEDS = [1, 2, 3, 4, 5]


def make_variant(scen, seed):
    src = os.path.join(SCEN, scen)
    dst = os.path.join(SCEN, f"{scen}_s{seed}")
    rou_src = os.path.join(src, f"{scen}.rou.xml")
    txt = io.open(rou_src, encoding="utf-8").read()
    md = re.search(r'<min-distance value="([0-9.]+)"', txt).group(1)
    period = re.search(r'<period value="([0-9.]+)"', txt).group(1)
    end = re.search(r'<end value="([0-9.]+)"', txt).group(1)
    vtype = re.search(r"<vType [^>]*/>", txt)
    vtype = vtype.group(0) if vtype else None

    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    for name in [f"{scen}.net.xml", f"{scen}.poly.xml", f"{scen}.sumo.cfg"]:
        shutil.copyfile(os.path.join(src, name), os.path.join(dst, name))
    with io.open(os.path.join(dst, "ipfeia.launchd.xml"), "w", encoding="utf-8") as f:
        f.write("<launch>\n"
                f'    <basedir path="scenarios/{scen}_s{seed}" />\n'
                f'    <copy file="{scen}.net.xml" />\n'
                f'    <copy file="{scen}.rou.xml" />\n'
                f'    <copy file="{scen}.sumo.cfg" type="config" />\n'
                "</launch>\n")

    rou_dst = os.path.join(dst, f"{scen}.rou.xml")
    subprocess.run([PY, os.path.join(TOOLS, "randomTrips.py"),
                    "-n", os.path.join(dst, f"{scen}.net.xml"), "-r", rou_dst,
                    "-b", "0", "-e", end, "-p", period,
                    "--min-distance", md, "--seed", str(seed)],
                   check=True, capture_output=True)
    t = io.open(rou_dst, encoding="utf-8").read()
    if vtype:
        if "<vType " in t:
            t = re.sub(r"<vType [^>]*/>", vtype, t, count=1)
        else:
            t = re.sub(r"(<routes[^>]*>)", lambda m: m.group(1) + "\n  " + vtype, t, count=1)
    t = t.replace("<vehicle ", '<vehicle type="car" ')
    io.open(rou_dst, "w", encoding="utf-8").write(t)
    n = t.count("<vehicle ")
    print(f"{scen}_s{seed}: {n} vehicles", flush=True)


if __name__ == "__main__":
    for s in BASE:
        for sd in SEEDS:
            make_variant(s, sd)

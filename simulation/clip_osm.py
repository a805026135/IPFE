"""Clip an OpenStreetMap XML extract to a latitude/longitude box.

Everything outside the box is dropped: a node is kept when it lies inside, and a
way is kept only when all of its nodes are kept. Used because the Overpass
recursion pulls in the far ends of long roads that cross the area of interest,
which would otherwise blow up the SUMO network extent.

Usage:
    python clip_osm.py <in.osm> <out.osm> <west> <south> <east> <north>
"""
import sys
import xml.etree.ElementTree as ET

src, dst = sys.argv[1], sys.argv[2]
west, south, east, north = (float(v) for v in sys.argv[3:7])

root = ET.parse(src).getroot()
nodes = {n.get("id"): n for n in root.findall("node")}
ways = root.findall("way")


def inside(node):
    return south <= float(node.get("lat")) <= north and west <= float(node.get("lon")) <= east


keep_nodes = {i for i, n in nodes.items() if inside(n)}
keep_ways = []
for w in ways:
    refs = [nd.get("ref") for nd in w.findall("nd")]
    if refs and all(r in keep_nodes for r in refs):
        keep_ways.append(w)

out = ET.Element("osm", {"version": "0.6", "generator": "clip_osm.py"})
used = set()
for w in keep_ways:
    for nd in w.findall("nd"):
        used.add(nd.get("ref"))
for i in sorted(used, key=int):
    out.append(nodes[i])
for w in keep_ways:
    out.append(w)
ET.ElementTree(out).write(dst, encoding="utf-8", xml_declaration=True)

print(f"nodes {len(nodes)} -> {len(used)}, ways {len(ways)} -> {len(keep_ways)}")

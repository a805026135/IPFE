#!/bin/bash
# Smoke test: runs one short simulation (c20_v50, O2M_AGG) end to end.
# Prerequisites and the expected directory layout are described in README.md.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../simenv.sh"
cd "$HERE"
./run_sim.sh O2M_AGG c20_v50
echo SMOKE_OK

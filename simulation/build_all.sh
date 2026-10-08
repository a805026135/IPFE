#!/bin/bash
#
# One-shot build of the IPFE-IA simulation stack (run inside an OMNeT++ shell):
#   1. source the OMNeT++ 6.0.1 environment
#   2. build Veins 5.2            -> veins-src/src/libveins.dll
#   3. build the IPFE-IA project  -> veins-ipfeia/src/libipfeia.dll
#
# Usage (from Windows PowerShell):
#   & omnetpp-6.0.1\tools\win32.x86_64\usr\bin\bash.exe -l -c \
#     "cd <simulation> && ./build_all.sh"
#
set -e
SIM_ROOT=$(cd "$(dirname "$0")" && pwd)
OMNETPP_ROOT=${OMNETPP_ROOT:-$SIM_ROOT/omnetpp-6.0.1}

if [ ! -f "$OMNETPP_ROOT/setenv" ]; then
  echo "Error: OMNeT++ not found at $OMNETPP_ROOT" >&2
  exit 1
fi
. "$OMNETPP_ROOT/setenv"

# native Windows python + SUMO from the local venv (used by run scripts)
if [ -f "$SIM_ROOT/venv/Scripts/python.exe" ]; then
  export PYTHON="$(cygpath -w "$SIM_ROOT/venv/Scripts/python.exe")"
  export SUMO="$(cygpath -w "$SIM_ROOT/venv/Scripts/sumo.exe")"
fi

echo "== OMNeT++ $OMNETPP_VERSION at $OMNETPP_ROOT =="

echo "== building Veins 5.2 =="
cd "$SIM_ROOT/veins-src"
if [ ! -f src/Makefile ]; then
  ./configure
fi
make -j4 MODE=release

echo "== building IPFE-IA simulation =="
cd "$SIM_ROOT/veins-ipfeia"
if [ ! -f src/Makefile ]; then
  ./configure --with-veins=../veins-src
fi
make -j4 MODE=release

echo ""
echo "build OK -- run simulations with: (cd veins-ipfeia && ./run_all.sh)"

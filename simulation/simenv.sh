#!/bin/bash
#
# Shared environment for running the IPFE-IA simulations from Git Bash (MINGW64).
#
#   source simenv.sh
#
# Why this exists: OMNeT++'s own "setenv" assumes it is sourced inside the
# OMNeT++ MSYS shell and prepends "/opt/mingw64/bin", which does not exist in
# Git Bash.  As a result libveins.dll/libipfeia.dll fail to locate liboppsim.dll
# and the MinGW runtime.  Here we prepend the REAL directories, in Windows form
# (what the native PE loader consumes), so every run is reproducible.
#
# Layout: this project needs three third-party trees that are NOT part of the
# repository.  They may sit either inside this directory (as in the authors'
# working tree) or next to it:
#
#   <work>/                       or   <work>/simulation/
#   ├── simulation/                    ├── omnetpp-6.0.1/
#   ├── omnetpp-6.0.1/                 ├── veins-src/
#   ├── veins-src/                     ├── venv/
#   └── venv/                          └── veins-ipfeia/   (this repository)
#
# Override any path by exporting it before sourcing this file.

SIM_ROOT="${SIM_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

# first existing candidate, else the first one (so error messages stay useful)
pick() { local c; for c in "$@"; do [ -e "$c" ] && { printf '%s' "$c"; return; }; done; printf '%s' "$1"; }

OPP_ROOT="${OPP_ROOT:-$(pick "$SIM_ROOT/omnetpp-6.0.1" "$SIM_ROOT/../omnetpp-6.0.1")}"
VEINS_SRC="${VEINS_SRC:-$(pick "$SIM_ROOT/veins-src" "$SIM_ROOT/../veins-src")}"
VENV="${VENV:-$(pick "$SIM_ROOT/venv" "$SIM_ROOT/../venv")}"
MINGW_BIN="$OPP_ROOT/tools/win32.x86_64/mingw64/bin"

# Windows-form paths only where the native PE loader needs them.
if command -v cygpath >/dev/null 2>&1; then
  W() { cygpath -w "$1"; }
else
  W() { printf '%s' "$1"; }
fi

# Front-load the real DLL directories.
export PATH="$(W "$OPP_ROOT/bin"):$(W "$VEINS_SRC/src"):$(W "$SIM_ROOT/veins-ipfeia/src"):$(W "$MINGW_BIN"):$PATH"

# Re-usable by the wrapper scripts.
export SIM_ROOT OPP_ROOT VEINS_SRC VENV

# OMNeT++ base variables (setenv would clobber PATH, so set the essentials here).
export __omnetpp_root_dir="$OPP_ROOT"
export OMNETPP_RELEASE="$(cat "$OPP_ROOT/Version" 2>/dev/null)"
export OMNETPP_ROOT="$OPP_ROOT"
export PYTHONPATH="$OPP_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"

# Third-party tools used by the Veins/SUMO coupling.
if [ -x "$VENV/Scripts/sumo.exe" ]; then
  export SUMO="$VENV/Scripts/sumo.exe"; export PYTHON="$VENV/Scripts/python.exe"
elif [ -x "$VENV/bin/sumo" ]; then
  export SUMO="$VENV/bin/sumo";        export PYTHON="$VENV/bin/python"
fi

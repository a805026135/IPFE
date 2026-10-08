#!/bin/bash
#
# Run one IPFE-IA simulation.
#
#   ./run_sim.sh <Config> <scenario> [extra opp_run args...]
#
# Example:
#   ./run_sim.sh O2M_AGG c100_v50
#
# Prerequisites (see README.md):
#   - OMNeT++ shell (source setenv), veins-src built, this project built (make)
#   - SUMO available (SUMO env var, ../venv/Scripts/sumo.exe, or in PATH)
#
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
VEINS=$(cd "$HERE/../veins-src" && pwd)
# Make the environment reproducible when invoked from Git Bash: source the
# shared helper (OMNeT++ bin + MinGW runtime + our lib dirs on PATH).
[ -f "$HERE/../simenv.sh" ] && . "$HERE/../simenv.sh"
CONFIG=${1:-O2M_AGG}
SCENARIO=${2:-c100_v50}
shift 2 || true

RESULTS="${OUTDIR:-$HERE/results}"
mkdir -p "$RESULTS"
LOG="$RESULTS/${SCENARIO}_${CONFIG}.log"

# --- locate the veins library -----------------------------------------------
for ext in so dll dylib; do
  if [ -f "$VEINS/src/libveins.$ext" ]; then VLIB="$VEINS/src/libveins.$ext"; break; fi
done
if [ -z "${VLIB:-}" ]; then
  echo "Error: libveins not found in $VEINS/src -- build veins first." >&2
  exit 1
fi

# --- locate our library ------------------------------------------------------
for ext in so dll dylib; do
  if [ -f "$HERE/src/libipfeia.$ext" ]; then PLIB="$HERE/src/libipfeia.$ext"; break; fi
done
if [ -z "${PLIB:-}" ]; then
  echo "Error: libipfeia not found in $HERE/src -- run make first." >&2
  exit 1
fi

# --- locate SUMO and the python that runs sumo-launchd ----------------------
SUMO=${SUMO:-}
if [ -z "$SUMO" ]; then
  for c in "$HERE/../venv/Scripts/sumo.exe" "$HERE/../venv/bin/sumo" "$(command -v sumo || true)"; do
    if [ -n "$c" ] && [ -f "$c" ]; then SUMO="$c"; break; fi
  done
fi
if [ -z "$SUMO" ]; then
  echo "Error: SUMO not found -- set the SUMO environment variable." >&2
  exit 1
fi
PY=${PYTHON:-python3}
command -v "$PY" >/dev/null 2>&1 || PY=python

# A native (Windows) opp_run.exe loads DLLs through the PE loader, which only
# understands Windows-form paths.  Convert when cygpath is available (Git Bash /
# MSYS); on Linux/macOS this is a no-op so the script stays portable.
winpath() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}

# --- start sumo-launchd ------------------------------------------------------
# (must run from $HERE: launchd.xml <basedir> paths are relative to its CWD)
cd "$HERE"
LAUNCHD="$(winpath "$VEINS/bin/veins_launchd")"
PORT=${LAUNCHD_PORT:-9999}
"$PY" "$LAUNCHD" -p "$PORT" -c "$SUMO" &
LAUNCHD_PID=$!
trap 'kill $LAUNCHD_PID 2>/dev/null || true' EXIT
sleep 2

# --- run ----------------------------------------------------------------------
echo "Running Config=$CONFIG scenario=$SCENARIO -> $LOG"
opp_run -u Cmdenv \
  -n "$(winpath "$HERE/src");$(winpath "$VEINS/src/veins")" \
  -l "$(winpath "$VLIB")" -l "$(winpath "$PLIB")" \
  -c "$CONFIG" \
  "--**.manager.launchConfig=xmldoc(\"scenarios/${SCENARIO}/ipfeia.launchd.xml\")" \
  "${INI:-omnetpp.ini}" "$@" > "$LOG" 2>&1

echo "done."

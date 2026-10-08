#!/usr/bin/env bash
#
# Launch the Veins simulation in Qtenv (GUI) with the real campus map canvas.
# Used to capture the run-time screenshot of the simulation (Fig. 9).
#
# Windows/Git-Bash only: it drives the Qtenv window through the OMNeT++ shell
# and sends keystrokes with the helper scripts (_maxzoom.py, _keys.py).
#
# Layout: see simenv.sh.  Override SIM_ROOT before calling if your tree differs.
set -u

SIM_ROOT="${SIM_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
. "$SIM_ROOT/simenv.sh"

LOG="${LOG:-$SIM_ROOT/qtenv_run.log}"
: > "$LOG"

echo "[1] starting veins_launchd" >> "$LOG"
# launchd resolves the launch XML's relative basedir against its own cwd,
# so it must run from veins-ipfeia (same as run_sim.sh does)
cd "$SIM_ROOT/veins-ipfeia"
"$PYTHON" "$VEINS_SRC/bin/veins_launchd" -p 9999 -c "$SUMO" >> "$LOG" 2>&1 &
LAUNCHD=$!
sleep 3

echo "[2] starting opp_run Qtenv" >> "$LOG"
opp_run -u Qtenv \
  -l liboppqtenv.dll \
  -n "$PWD/src:$VEINS_SRC/src/veins" \
  -l "$VEINS_SRC/src/libveins.dll" -l "$PWD/src/libipfeia.dll" \
  -c GUI omnetpp.ini >> "$LOG" 2>&1 &
OPPRUN=$!

# While Qtenv still holds focus (it takes it on startup), drive it:
# maximize the window, zoom out so the whole network fits, then
# express-run to the 120 s sim-time limit.
sleep 20
"$PYTHON" "$SIM_ROOT/_maxzoom.py" Qtenv 1 in >> "$LOG" 2>&1
sleep 3
"$PYTHON" "$SIM_ROOT/_keys.py" Qtenv F7 >> "$LOG" 2>&1
sleep 10
"$PYTHON" "$SIM_ROOT/_keys.py" Qtenv F7 >> "$LOG" 2>&1
sleep 12
"$PYTHON" "$SIM_ROOT/_keys.py" Qtenv F7 >> "$LOG" 2>&1
sleep 15
echo "[3] keys sent, opp_run alive: $(kill -0 $OPPRUN 2>/dev/null && echo yes || echo no)" >> "$LOG"
wait $OPPRUN
echo "[4] opp_run exited: $?" >> "$LOG"
kill $LAUNCHD 2>/dev/null

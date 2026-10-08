#!/bin/bash
#
# R3 (cont.): harsher propagation at REALISTIC coverage.
#
# The first alpha = 3.0 batch used the same 20 dBm transmit power as the main
# runs, which shortens the effective range from ~1140 m to ~110 m and starves
# the 25-RSU deployment of coverage -- that is a coverage artefact of the
# single-slope model, not an urban propagation scenario.  Here the exponent is
# kept at 3.0 but the transmit power is raised to the 802.11p maximum
# (33 dBm / 2000 mW), which restores the range to ~300 m: a realistic urban
# value.  This isolates the effect of the harsher exponent at unchanged,
# realistic coverage.
#
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VEINS_DIR="$SIM/veins-ipfeia"
. "$SIM/simenv.sh"
cd "$VEINS_DIR"

LOG="$SIM/revision_round3b.log"
SCA="$VEINS_DIR/results/_sca"
OUT="$VEINS_DIR/results_alpha3_33dbm"
mkdir -p "$SCA" "$OUT"
: > "$LOG"

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

run_job() {
  local scen=$1 slot=$2 port i n
  port=$((14000 + slot))
  local seed="${scen##*_s}"
  for i in 1 2 3; do
    if OUTDIR="$OUT" INI=omnetpp_alpha3_33dbm.ini LAUNCHD_PORT=$port ./run_sim.sh O2M_AGG "$scen" \
        "--seed-set=${seed}" \
        "--**.manager.port=${port}" \
        "--output-scalar-file=$(cygpath -w "$SCA/r3b_slot${slot}.sca")" \
        >> "$LOG" 2>&1; then
      n=$(grep -c "VEH_SUMMARY" "$OUT/${scen}_O2M_AGG.log" 2>/dev/null); n=${n:-0}
      if [ "$n" -gt 0 ]; then say "OK   $scen veh=${n}"; return 0; fi
      say "EMPTY $scen (attempt $i)"
    else
      say "FAIL $scen (attempt $i)"
    fi
    sleep 3
  done
  say "GIVE-UP $scen"
}

slot=0
for k in 1 2 3 4 5; do run_job "c100_v50_s${k}" "$((slot++))" & done
wait
for k in 1 2 3 4 5; do run_job "c500_v50_s${k}" "$((slot++))" & done
wait

say "ROUND3B_DONE"

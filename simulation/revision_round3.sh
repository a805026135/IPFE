#!/bin/bash
#
# Reviewer round 3:
#   (R2) re-run the one broken seed run  c500_v50_s5_O2O_AGG  (its log had
#        VEH_SUMMARY=0, so the one-to-one variant had no 500-vehicle data point)
#   (R3) robustness batch under an urban empirical path-loss exponent
#        (alpha = 3.0 instead of 2.0, see config_alpha3.xml / omnetpp_alpha3.ini),
#        O2M_AGG at 100 and 500 vehicles, five seeds each, written to
#        results_alpha3/ so the main result set is untouched.
#
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VEINS_DIR="$SIM/veins-ipfeia"
. "$SIM/simenv.sh"
cd "$VEINS_DIR"

LOG="$SIM/revision_round3.log"
SCA="$VEINS_DIR/results/_sca"
mkdir -p "$SCA" "$VEINS_DIR/results_alpha3"
: > "$LOG"
NWORK=${NWORK:-5}

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

run_job() {   # run_job <scenario> <config> <ini> <outdir> <slot>
  local scen=$1 cfg=$2 ini=$3 outdir=$4 slot=$5
  local port=$((13000 + slot)) seed i n
  seed="${scen##*_s}"; case "$seed" in *[!0-9]*) seed="";; esac
  local extra=()
  [ -n "$seed" ] && extra+=("--seed-set=${seed}")
  for i in 1 2 3; do
    if OUTDIR="$outdir" INI="$ini" LAUNCHD_PORT=$port ./run_sim.sh "$cfg" "$scen" \
        "${extra[@]}" \
        "--**.manager.port=${port}" \
        "--output-scalar-file=$(cygpath -w "$SCA/r3_slot${slot}.sca")" \
        >> "$LOG" 2>&1; then
      local f="$outdir/${scen}_${cfg}.log"
      n=$(grep -c "VEH_SUMMARY" "$f" 2>/dev/null); n=${n:-0}
      if [ "$n" -gt 0 ]; then say "OK   $scen $cfg [$ini -> $outdir] veh=${n}"; return 0; fi
      say "EMPTY $scen $cfg (attempt $i)"
    else
      say "FAIL $scen $cfg (attempt $i)"
    fi
    sleep 3
  done
  say "GIVE-UP $scen $cfg"
  return 1
}

say "queued 11 jobs, ${NWORK} workers"

slot=0
pids=()
run_job c500_v50_s5 O2O_AGG omnetpp.ini results "$((slot++))" & pids+=($!)
for k in 1 2 3 4 5; do
  run_job "c100_v50_s${k}" O2M_AGG omnetpp_alpha3.ini results_alpha3 "$((slot++))" & pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done

for k in 1 2 3 4 5; do
  run_job "c500_v50_s${k}" O2M_AGG omnetpp_alpha3.ini results_alpha3 "$((slot++))" &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done

say "ROUND3_DONE"
say "alpha3 logs: $(ls results_alpha3/*.log 2>/dev/null | wc -l)"

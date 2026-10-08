#!/bin/bash
#
# Reviewer-response experiment queue (runs in the background, sequentially):
#   A) parameter sensitivity  -- aggregation window & re-authentication period
#   B) RSU density            -- 15 / 35 RSUs instead of 25
#   C) repeated runs          -- 5 seeds x (5 fleet sizes x {O2M,O2O}) + 3 speeds
#
SIM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SIM_ROOT/simenv.sh"
cd "$SIM_ROOT/veins-ipfeia"
LOG="$SIM_ROOT/revision_experiments.log"
: > "$LOG"

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# run one simulation with up to 3 attempts (transient TraCI/launchd failures)
run_one() {   # run_one <config> <scenario> [extra args...]
  local cfg=$1 scen=$2; shift 2
  local i
  for i in 1 2 3; do
    if ./run_sim.sh "$cfg" "$scen" "$@" >> "$LOG" 2>&1; then
      return 0
    fi
    say "retry $i for $cfg/$scen"
    sleep 5
  done
  say "FAILED after 3 attempts: $cfg/$scen"
  return 1
}

# ---------- A) parameter sensitivity --------------------------------------
say "A1: aggregation window sweep (c100_v50, 1/10/20 s)"
for W in 1 10 20; do
  run_one O2M_AGG c100_v50 "--**.rsu[*].appl.aggWindow=${W}s" || true
  mv results/c100_v50_O2M_AGG.log "results/sens_aggw${W}_c100.log" 2>/dev/null || true
done
say "A2: aggregation window at c200 (1/20 s)"
for W in 1 20; do
  run_one O2M_AGG c200_v50 "--**.rsu[*].appl.aggWindow=${W}s" || true
  mv results/c200_v50_O2M_AGG.log "results/sens_aggw${W}_c200.log" 2>/dev/null || true
done
say "A3: re-authentication period sweep (c100_v50, 10/60 s)"
for R in 10 60; do
  run_one O2M_AGG c100_v50 "--**.node[*].appl.reauthInterval=${R}s" || true
  mv results/c100_v50_O2M_AGG.log "results/sens_reauth${R}.log" 2>/dev/null || true
done

# ---------- B) RSU density --------------------------------------------------
say "B: RSU density variants (15 / 35 RSUs)"
for K in 15 35; do
  for S in c100_v50 c500_v50; do
    run_one O2M_AGG "$S" "omnetpp_r${K}.ini" || true
    mv "results/${S}_O2M_AGG.log" "results/dens_r${K}_${S}.log" 2>/dev/null || true
  done
done

# ---------- C) repeated runs with independent seeds -------------------------
say "C: repeated runs, 5 seeds"
for SD in 1 2 3 4 5; do
  for CFG in O2M_AGG O2O_AGG; do
    for S in c20_v50 c50_v50 c100_v50 c200_v50 c500_v50; do
      run_one "$CFG" "${S}_s${SD}" "--seed-set=${SD}" || true
    done
  done
  for S in c100_v30 c100_v80 c100_v120; do
    run_one O2M_AGG "${S}_s${SD}" "--seed-set=${SD}" || true
  done
  say "seed ${SD} done: $(ls results/*_s${SD}_*.log 2>/dev/null | wc -l)/13 runs"
done
say "ALL_REVISION_EXPERIMENTS_DONE"

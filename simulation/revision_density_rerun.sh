#!/bin/bash
#
# Waits for the main revision queue to finish, then re-runs the RSU-density
# experiments.  The first attempt passed the density ini as an EXTRA ini file,
# which the main omnetpp.ini silently overrode (all runs used 25 RSUs); here
# run_sim.sh is invoked with INI=<density ini> so omnetpp.ini is replaced.
#
SIM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SIM_ROOT/revision_density_rerun.log"
: > "$LOG"

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "waiting for the main queue to finish"
while ! grep -q "ALL_REVISION_EXPERIMENTS_DONE" "$SIM_ROOT/revision_experiments.log" 2>/dev/null; do
  sleep 60
done
say "main queue finished - starting density rerun"

. "$SIM_ROOT/simenv.sh"
cd "$SIM_ROOT/veins-ipfeia"

for K in 15 35; do
  for S in c100_v50 c500_v50; do
    for i in 1 2 3; do
      if INI="omnetpp_r${K}.ini" ./run_sim.sh O2M_AGG "$S" >> "$LOG" 2>&1; then break; fi
      say "retry $i for r${K}/${S}"
      sleep 5
    done
    mv "results/${S}_O2M_AGG.log" "results/dens_r${K}_${S}.log" 2>/dev/null || true
    n=$(grep -ac "RSU_SUMMARY" "results/dens_r${K}_${S}.log" 2>/dev/null || echo 0)
    say "r${K} ${S}: RSUs in run = ${n}"
  done
done
say "DENSITY_RERUN_DONE"

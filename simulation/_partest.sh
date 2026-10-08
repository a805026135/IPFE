#!/bin/bash
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SIM/simenv.sh"
cd "$SIM/veins-ipfeia"

run() {   # run <scen> <cfg> <port> <slot>
  local scen=$1 cfg=$2 port=$3 slot=$4
  LAUNCHD_PORT=$port ./run_sim.sh "$cfg" "$scen" "--seed-set=${scen##*_s}" \
    "--**.manager.port=$port" \
    "--output-scalar-file=results/${slot}.sca" \
    > "/tmp/par_${slot}.out" 2>&1
  echo "$slot exit=$? summary=$(grep -c SUMMARY results/${scen}_${cfg}.log 2>/dev/null)"
}

t0=$(date +%s)
run c50_v50_s3 O2M_AGG 11101 a &
run c100_v50_s3 O2M_AGG 11102 b &
wait
echo "elapsed=$(( $(date +%s) - t0 ))s"
cat /tmp/par_a.out /tmp/par_b.out | tail -6

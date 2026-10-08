#!/bin/bash
#
# M4: run the batch/broadcast-class baseline (CMP_BLS_BATCH) across the five
# fleet sizes, single run each (like the other signature-based competitors,
# which are deterministic given the measured primitive costs).
#
# Unique launchd port + unique scalar file per worker so the runs cannot collide.
#
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SIM/simenv.sh"
cd "$SIM/veins-ipfeia"

LOG="$SIM/revision_bls.log"
SCA="$SIM/veins-ipfeia/results/_sca"
mkdir -p "$SCA"
: > "$LOG"
NWORK=${NWORK:-5}

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

run_one() {   # run_one <scenario> <slot>
  local scen=$1 slot=$2
  local port=$((12000 + slot))
  local i
  for i in 1 2 3; do
    if LAUNCHD_PORT=$port ./run_sim.sh CMP_BLS_BATCH "$scen" \
        "--**.manager.port=${port}" \
        "--output-scalar-file=$(cygpath -w "$SCA/bls${slot}.sca")" \
        >> "$LOG" 2>&1; then
      local n
      n=$(grep -c "SUMMARY" "results/${scen}_CMP_BLS_BATCH.log" 2>/dev/null || echo 0)
      if [ "$n" -gt 0 ]; then say "OK   $scen CMP_BLS_BATCH (${n} rows)"; return 0; fi
      say "EMPTY $scen (attempt $i)"
    else
      say "FAIL $scen (attempt $i)"
    fi
    sleep 3
  done
  say "GIVE-UP $scen"
  return 1
}

slot=0
pids=()
for S in c20_v50 c50_v50 c100_v50 c200_v50 c500_v50; do
  run_one "$S" "$slot" &
  pids+=($!)
  slot=$((slot+1))
done
for p in "${pids[@]}"; do wait "$p"; done

say "BLS_BATCH_DONE"
ls -la results/*CMP_BLS_BATCH.log 2>/dev/null | tee -a "$LOG"

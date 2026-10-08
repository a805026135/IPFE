#!/bin/bash
#
# Re-run the two contaminated RSU-density jobs, strictly one at a time, each
# verified against its expected RSU count before being accepted.  Earlier runs
# raced on the shared results/<scenario>_O2M_AGG.log filename.
#
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SIM/simenv.sh"
cd "$SIM/veins-ipfeia"
LOG="$SIM/revision_density3.log"
: > "$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# one_at_a_time <K> <S> <expected_rsus>
one_at_a_time() {
  local K=$1 S=$2 want=$3 i n
  local tmp="results/_dens_r${K}_${S}.log"
  say "--- r${K} ${S} (expect ${want} RSUs) ---"
  for i in 1 2 3; do
    rm -f "$tmp" 2>/dev/null || true
    INI="omnetpp_r${K}.ini" LAUNCHD_PORT=$((12100+K)) \
      ./run_sim.sh O2M_AGG "$S" \
      "--**.manager.port=$((12100+K))" \
      "--output-scalar-file=$(cygpath -w "$SIM/veins-ipfeia/results/_sca/d3.sca")" \
      >> "$LOG" 2>&1
    # run_sim.sh writes results/${S}_O2M_AGG.log -- move it away IMMEDIATELY
    mv -f "results/${S}_O2M_AGG.log" "$tmp" 2>/dev/null || true
    n=$(grep -c RSU_SUMMARY "$tmp" 2>/dev/null || echo 0)
    if [ "$n" = "$want" ]; then
      mv -f "$tmp" "results/dens_r${K}_${S}.log"
      say "OK   r${K} ${S}: ${n} RSUs"
      return 0
    fi
    say "BAD  r${K} ${S}: got ${n} RSUs, want ${want} (attempt ${i})"
    sleep 3
  done
  say "GIVE-UP r${K} ${S}"
  return 1
}

one_at_a_time 15 c100_v50 15
one_at_a_time 35 c500_v50 35

say "DENSITY3_DONE"
for K in 15 35; do for S in c100_v50 c500_v50; do
  echo "  dens_r${K}_${S}: $(grep -c RSU_SUMMARY results/dens_r${K}_${S}.log 2>/dev/null || echo 0) RSUs" | tee -a "$LOG"
done; done

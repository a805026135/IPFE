#!/bin/bash
#
# RSU-density reruns only.  The 15/35-RSU variants must REPLACE the earlier
# invalid artifacts (those runs silently used the 25-RSU default because the
# density ini was passed as an extra file and overridden by omnetpp.ini).
#
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SIM/simenv.sh"
cd "$SIM/veins-ipfeia"
LOG="$SIM/revision_density2.log"
: > "$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

for K in 15 35; do
  for S in c100_v50 c500_v50; do
    out="results/dens_r${K}_${S}.log"
    ok=0
    for i in 1 2 3; do
      if INI="omnetpp_r${K}.ini" LAUNCHD_PORT=$((12000+K)) ./run_sim.sh O2M_AGG "$S" \
           "--**.manager.port=$((12000+K))" \
           "--output-scalar-file=$(cygpath -w "$SIM/veins-ipfeia/results/_sca/dens.sca")" >> "$LOG" 2>&1; then
        n=$(grep -c RSU_SUMMARY "results/${S}_O2M_AGG.log" 2>/dev/null || echo 0)
        if [ "$n" -gt 0 ]; then
          mv -f "results/${S}_O2M_AGG.log" "$out"
          say "OK r${K} ${S}: ${n} RSUs"
          ok=1; break
        fi
      fi
      say "retry $i r${K}/${S}"
      sleep 5
    done
    [ "$ok" = 0 ] && say "GIVE-UP r${K}/${S}"
  done
done
say "DENSITY2_DONE"
for K in 15 35; do for S in c100_v50 c500_v50; do
  echo "  dens_r${K}_${S}: $(grep -c RSU_SUMMARY results/dens_r${K}_${S}.log 2>/dev/null || echo 0) RSUs" | tee -a "$LOG"
done; done

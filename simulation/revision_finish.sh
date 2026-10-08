#!/bin/bash
#
# Parallel completion queue for the reviewer-response experiments.
#
# Finishes what revision_experiments.sh left unfinished (the previous session
# ended mid-queue, and run_sim.sh had two Windows/DLL path bugs that made every
# run fail):
#   C) seed repeats   -- the 34 missing <scenario>_s<k> runs
#   B) RSU density    -- 15/35 RSU variants (first attempt silently used 25)
#
# Uses a worker pool (default 5) with a unique launchd port and scalar file per
# worker so runs cannot collide, and retries each job up to 3 times -- a
# simulation is ~45-90 s, so 38 jobs finish in roughly ten minutes.
#
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SIM/simenv.sh"
cd "$SIM/veins-ipfeia"

JOBS="$SIM/_jobs.txt"
LOG="$SIM/revision_finish.log"
SCA="$SIM/veins-ipfeia/results/_sca"
mkdir -p "$SCA"
: > "$LOG"
NWORK=${NWORK:-5}

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# ---- job list: "<scenario> <config> [INI=<file>]" --------------------------
: > "$JOBS"
for k in 3 4 5; do
  for S in c20_v50 c50_v50 c100_v50 c200_v50 c500_v50; do
    for C in O2M_AGG O2O_AGG; do
      f="results/${S}_s${k}_${C}.log"
      [ -s "$f" ] || echo "${S}_s${k} ${C}" >> "$JOBS"
    done
  done
  for S in c100_v30 c100_v80 c100_v120; do
    f="results/${S}_s${k}_O2M_AGG.log"
    [ -s "$f" ] || echo "${S}_s${k} O2M_AGG" >> "$JOBS"
  done
done
# (density reruns are appended after the pool below -- they reuse the same
#  scenario names, so running them concurrently would clobber each other)

total=$(wc -l < "$JOBS")
say "queued ${total} seed jobs, ${NWORK} workers"

# ---- one job ---------------------------------------------------------------
run_job() {   # run_job <line> <slot>
  local line=$1 slot=$2
  local scen cfg ini out
  read -r scen cfg ini out <<< "$(echo "$line" | sed 's/OUT=/OUT=/')"
  local extra=()
  local outname="${scen}_${cfg}.log"
  for tok in $line; do
    case "$tok" in
      INI=*) ini="${tok#INI=}" ;;
      OUT=*) outname="${tok#OUT=}" ;;
    esac
  done
  local port=$((11000 + slot))
  local seed="${scen##*_s}"; case "$seed" in *[!0-9]*) seed="";; esac
  [ -n "$seed" ] && extra+=("--seed-set=${seed}")

  local i
  for i in 1 2 3; do
    if INI="${ini:-omnetpp.ini}" LAUNCHD_PORT=$port ./run_sim.sh "$cfg" "$scen" \
        "${extra[@]}" \
        "--**.manager.port=${port}" \
        "--output-scalar-file=$(cygpath -w "$SCA/slot${slot}.sca")" \
        >> "$LOG" 2>&1; then
      # density runs must be renamed after the fact (run_sim.sh names by scenario)
      if [ "$outname" != "${scen}_${cfg}.log" ]; then
        mv -f "results/${scen}_${cfg}.log" "results/${outname}" 2>/dev/null || true
      fi
      logf="results/${outname}"
      n=$(grep -c "SUMMARY" "$logf" 2>/dev/null || echo 0)
      if [ "$n" -gt 0 ]; then say "OK   $scen $cfg -> $outname (${n} rows)"; return 0; fi
      say "EMPTY $scen $cfg (attempt $i)"
    else
      say "FAIL $scen $cfg (attempt $i)"
    fi
    sleep 3
  done
  say "GIVE-UP $scen $cfg"
  return 1
}

# ---- worker pool -----------------------------------------------------------
worker() {   # worker <slot>
  local slot=$1 line
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    run_job "$line" "$slot"
  done < <(awk -v s="$slot" -v n="$NWORK" 'NR % n == s % n' "$JOBS")
}

pids=()
for s in $(seq 0 $((NWORK-1))); do
  worker "$s" &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
say "seed pool finished: $(ls results/*_s[1-5]_*.log 2>/dev/null | wc -l)/65"

# ---- density reruns, serialised (same scenario names as the seed pool) ------
say "B: RSU density reruns (15 / 35 RSUs)"
slot=90
for K in 15 35; do
  for S in c100_v50 c500_v50; do
    slot=$((slot+1))
    run_job "${S} O2M_AGG INI=omnetpp_r${K}.ini OUT=dens_r${K}_${S}.log" "$slot"
    n=$(grep -c "RSU_SUMMARY" "results/dens_r${K}_${S}.log" 2>/dev/null || echo 0)
    say "   dens_r${K}_${S}: ${n} RSU rows"
  done
done

say "REVISION_FINISH_DONE"
say "seed logs: $(ls results/*_s[1-5]_*.log 2>/dev/null | wc -l)/65"

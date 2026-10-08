#!/bin/bash
#
# Run the full IPFE-IA experiment matrix, ~300 s sim-time each.
#
# Experiment design (see paper Sec. "Simulation Evaluation"):
#   E1 fleet size scaling   : c20/c50/c100/c200/c500 @ 50 km/h, O2M_AGG
#   E2 speed impact         : c100 @ 30/50/80/120 km/h, O2M_AGG
#   E3 mode comparison      : c100_v50 with O2M_AGG / O2M_PAPER / O2O_AGG / O2O_PAPER
#   E4 one-to-one baseline  : c20/c50/c200/c500 @ 50 km/h, O2O_AGG
#                             (empirical baseline curve for the scalability
#                              comparison; c100_v50 is already in E3)
#
set -e
HERE=$(cd "$(dirname "$0")" && pwd)

# E1: fleet size scaling (5 runs)
for S in c20_v50 c50_v50 c100_v50 c200_v50 c500_v50; do
  "$HERE/run_sim.sh" O2M_AGG "$S"
done

# E2: speed impact (3 more runs; c100_v50 already in E1)
for S in c100_v30 c100_v80 c100_v120; do
  "$HERE/run_sim.sh" O2M_AGG "$S"
done

# E3: authentication/decryption mode comparison (3 more runs)
for C in O2M_PAPER O2O_AGG O2O_PAPER; do
  "$HERE/run_sim.sh" "$C" c100_v50
done

# E4: one-to-one baseline scaling (4 more runs)
for S in c20_v50 c50_v50 c200_v50 c500_v50; do
  "$HERE/run_sim.sh" O2O_AGG "$S"
done

# E5: representative one-to-one competitors over the fleet range (15 runs)
for C in CMP_HE2023 CMP_HASSAN2022 CMP_SEIFELNASR2024; do
  for S in c20_v50 c50_v50 c100_v50 c200_v50 c500_v50; do
    "$HERE/run_sim.sh" "$C" "$S"
  done
done

echo "All runs finished. Analyze with: python3 analyze.py"

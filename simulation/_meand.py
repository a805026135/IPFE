# -*- coding: utf-8 -*-
"""Mean number of ciphertexts per AS decryption window (the 'mean d' of the
decryption paragraph), over the 5 seeds at 100 vehicles."""
import glob, os, statistics, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "veins-ipfeia", "results")

ds_all = []
for p in sorted(glob.glob(os.path.join(RES, "c100_v50_s*_O2M_AGG.log"))):
    ds = []
    with open(p, "r", errors="replace") as f:
        for line in f:
            if line.startswith("IPFEIA_LOG,AS_DEC,"):
                q = line.strip().split(",")
                try:
                    ds.append(int(q[3]))   # IPFEIA_LOG,AS_DEC,<t>,<d>,<n>,<ms>,<mode>
                except (ValueError, IndexError):
                    pass
    ds_all += ds
    if ds:
        print(f"{os.path.basename(p)[:26]:26s} windows={len(ds):4d} mean d={statistics.mean(ds):5.2f}")
    else:
        print(f"{os.path.basename(p)[:26]:26s} windows=0 (no AS_DEC lines)")

print(f"\noverall      windows={len(ds_all)} mean d={statistics.mean(ds_all):.2f}" if ds_all else "\nno data")
print(f"per-ciphertext delay 62.157 ms  -> mean cost {statistics.mean(ds_all)*62.157:.1f} ms")
print(f"aggregated    62.157 ms        -> saving factor {statistics.mean(ds_all):.2f}x")
print(f"d=9 cost {9*62.157:.1f} ms")

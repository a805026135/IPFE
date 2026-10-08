import os, re, glob
RES = "results"
bases = ["c20_v50","c50_v50","c100_v50","c200_v50","c500_v50","c100_v30","c100_v80","c100_v120"]
cfgs  = ["O2M_AGG","O2O_AGG"]
# expectation: fleet scenarios need both cfgs; speed scenarios only O2M
need = {}
for b in bases:
    for c in cfgs:
        if b.startswith("c100_v") and b not in ("c100_v50",) and c=="O2O_AGG":
            continue
        need[(b,c)] = [f"{b}_s{k}_{c}.log" for k in range(1,6)]

print("=== seed-run matrix (present/needed) ===")
total_need = total_have = 0
missing = []
for (b,c), files in need.items():
    have = [f for f in files if os.path.exists(os.path.join(RES,f))]
    total_need += len(files); total_have += len(have)
    miss = [f for f in files if not os.path.exists(os.path.join(RES,f))]
    missing += miss
    print(f"  {b:9s} {c:9s} {len(have)}/{len(files)}" + ("" if not miss else "   MISS: "+",".join(os.path.basename(m) for m in miss)))
print(f"\nTOTAL {total_have}/{total_need}")
print(f"\n{len(missing)} runs missing:")
for m in missing: print("   ", m)

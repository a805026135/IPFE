# -*- coding: utf-8 -*-
"""Confidence-interval analysis of the repeated runs (reviewer M1).

Reads every results/*.log, groups the seed variants (<scenario>_s<k>) by base
scenario and re-draws the paper figures with 95% confidence intervals.
Writes results/figs/latency.png and results/figs/scalability.png (CI versions)
and prints the values needed in the text.
"""
import glob
import io
import re
import math
import os
import statistics
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "veins-ipfeia", "results")
sys.path.insert(0, os.path.join(HERE, "veins-ipfeia"))
import analyze  # noqa: E402

T95 = {2: 12.71, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365,
       9: 2.306, 10: 2.262, 11: 2.228, 12: 2.201, 13: 2.179, 14: 2.160,
       15: 2.145, 16: 2.131, 18: 2.110, 20: 2.093}


def ci95(values):
    # Drop NaN entries (a run whose counter was never exercised) -- Python's
    # statistics.stdev raises on NaN in recent versions.
    values = [v for v in values if v is not None and not math.isnan(v)]
    n = len(values)
    if n < 2:
        return 0.0
    sd = statistics.stdev(values)
    return T95.get(n, 1.96) * sd / math.sqrt(n)


def load():
    """{(config, base_scenario): [metric dict, ...]} from the seed runs."""
    groups = {}
    for path in sorted(glob.glob(os.path.join(RES, "*.log"))):
        name = os.path.basename(path)[:-4]
        try:
            d = analyze.parse_log(path).finish()
        except Exception as exc:  # noqa: BLE001
            print("skip", name, exc)
            continue
        if not re.search(r"_s\d+$", d["scenario"]):
            continue  # only seed variants
        # c100_v50_s2 -> c100_v50 ; c100_v120_s3 -> c100_v120
        base = d["scenario"].rsplit("_s", 1)[0]
        groups.setdefault((d["config"], base), []).append(d)
    return groups


def load_baselines():
    """Single-run competitor configs, keyed (config, scenario).

    The competing schemes were run once (they are deterministic given the
    measured primitive costs), so they are not part of the seed pool.
    """
    out = {}
    for path in sorted(glob.glob(os.path.join(RES, "*.log"))):
        name = os.path.basename(path)[:-4]
        if not re.search(r"_CMP_", name):
            continue
        try:
            d = analyze.parse_log(path).finish()
        except Exception as exc:  # noqa: BLE001
            print("skip baseline", name, exc)
            continue
        out.setdefault(d["scenario"], {})[d["config"]] = d
    return out


def load_dec_points():
    """config -> [(d, delay_ms)] for the 100-vehicle runs.

    Seed variants (``<scenario>_s<k>``) are folded back onto their base
    scenario, so the aggregated curve is built from all five seeds of
    ``c100_v50`` -- the seed runs are named ``c100_v50_s<k>_...`` and do NOT
    end in ``_v50`` themselves, which is what previously left the aggregated
    curve empty and produced a one-curve decryption figure.
    """
    out = {}
    for path in sorted(glob.glob(os.path.join(RES, "*.log"))):
        m = analyze.parse_log(path)
        base = re.sub(r"_s\d+$", "", m.scenario)
        if not base.endswith("_v50") or m.fleet() != 100:
            continue
        out.setdefault(m.config, []).extend((dd, dl) for dd, _n, dl, _md in m.as_dec)
    return out


def flip_y(ax, values, errs):
    ax.errorbar([v for v in values], [e for e in errs])


def style(ax):
    """Minimal, clean axes: no grid, no top/right spines."""
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def load_rounds():
    """{(cfg, base): {run: [(resp, total_cost_ms), ...]}} per broadcast round.

    Pairs AS_DELTA (round -> d, delta cost) with AS_ACK (round -> resp); rounds
    without any response are kept with resp = 0 (they cost only the delta).
    """
    out = {}
    for path in sorted(glob.glob(os.path.join(RES, "*.log"))):
        name = os.path.basename(path)[:-4]
        m = re.search(r"(c\d+_v50)_s\d+_", name)
        if not m or "_O2M_AGG" not in name:
            continue
        base = m.group(1)
        cfg = "O2M_AGG"
        delta, ack = {}, {}
        for line in io.open(path, encoding="utf-8", errors="ignore"):
            if ",AS_DELTA," in line:
                p = line.strip().split(",")
                delta[p[3]] = (int(p[4]), float(p[5]))
            elif ",AS_ACK," in line:
                p = line.strip().split(",")
                ack[p[3]] = int(p[4])
        rounds = [(ack.get(r, 0),
                   c + (16.5094 + 0.0225 * ack[r] if r in ack else 0.0))
                  for r, (d, c) in delta.items()]
        out.setdefault((cfg, base), {})[name] = rounds
    return out


def main():
    g = load()
    bl = load_baselines()
    figs = os.path.join(RES, "figs")
    os.makedirs(figs, exist_ok=True)

    def clean(vals):
        return [v for v in vals if v is not None and not math.isnan(v)]

    def series(cfg, scen, key, scale=1.0):
        ds = g.get((cfg, scen), [])
        vals = clean([d[key] / scale for d in ds if d.get(key) is not None])
        return (statistics.mean(vals), ci95(vals), len(vals)) if vals else (float("nan"), 0, 0)

    print("=== repeated-run summary (mean +/- 95% CI, n) ===")
    for cfg in ("O2M_AGG", "O2O_AGG"):
        for scen in ("c20_v50", "c50_v50", "c100_v50", "c200_v50", "c500_v50"):
            if (cfg, scen) not in g:
                continue
            n = len(g[(cfg, scen)])
            pv = series(cfg, scen, "as_auth_per_authed_ms")
            jt = series(cfg, scen, "join_time_mean_ms", 1000.0)
            it = series(cfg, scen, "initial_latency_mean_ms", 1000.0)
            print(f"  {cfg:9s} {scen:9s} n={n}  as/veh={pv[0]:6.2f}+/-{pv[1]:.2f}  "
                  f"join={jt[0]:.2f}+/-{jt[1]:.2f}s  init={it[0]:.2f}+/-{it[1]:.2f}s")
    for scen in ("c100_v30", "c100_v80", "c100_v120"):
        if ("O2M_AGG", scen) in g:
            jt = series("O2M_AGG", scen, "join_time_mean_ms", 1000.0)
            print(f"  speed {scen:9s} n={len(g[('O2M_AGG', scen)])} join={jt[0]:.2f}+/-{jt[1]:.2f}s")

    print("=== competing schemes (single run each) ===")
    for scen in ("c20_v50", "c50_v50", "c100_v50", "c200_v50", "c500_v50"):
        row = bl.get(scen, {})
        bits = []
        for cfg in ("CMP_HE2023", "CMP_HASSAN2022", "CMP_SEIFELNASR2024", "CMP_BLS_BATCH"):
            if cfg in row:
                bits.append(f"{cfg.replace('CMP_','')}="
                            f"{row[cfg]['as_auth_per_authed_ms']:.2f}ms")
        if bits:
            print(f"  {scen:9s} " + "  ".join(bits))



    # ---------------- figure 1: scalability with CIs ----------------
    rounds = load_rounds()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 3.6))
    xs, ys, xe, ye = [], [], [], []
    for scen in ("c20_v50", "c50_v50", "c100_v50", "c200_v50", "c500_v50"):
        runs = rounds.get(("O2M_AGG", scen), {})
        if not runs:
            continue
        # per-round AS cost of broadcast rounds that collected >=1 response
        # (rounds without any response are charged only the 13.8 ms delta and
        # are reported separately in the text); run-level means, CI over runs
        costs, resps = [], []
        for run, rl in runs.items():
            served = [(r, c) for r, c in rl if r > 0]
            if not served:
                continue
            costs.append(statistics.mean([c for r, c in served]))
            resps.append(statistics.mean([r for r, c in served]))
        if not costs:
            continue
        ys.append(statistics.mean(costs)); ye.append(ci95(costs))
        xs.append(statistics.mean(resps)); xe.append(ci95(resps))
        print("  round-cost %s: %.2f+/-%.2f ms over %.2f+/-%.2f responses (n=%d)"
              % (scen, ys[-1], ye[-1], xs[-1], xe[-1], len(costs)))
    axL.errorbar(xs, ys, xerr=xe, yerr=ye, marker="o", capsize=3, label="one-to-many")
    axL.set_xlabel("responses per broadcast round\n"
                   "(fleet size left to right: 20/50/100/200/500)")
    axL.set_ylabel("AS computation per broadcast round (ms)")
    style(axL)
    axL.legend(fontsize=8, frameon=False)

    for cfg, mk, lb in (("O2M_AGG", "o", "proposed (one-to-many)"),
                        ("O2O_AGG", "s", "proposed, one-to-one variant")):
        pts = []
        for scen in ("c20_v50", "c50_v50", "c100_v50", "c200_v50", "c500_v50"):
            ds = g.get((cfg, scen), [])
            if not ds:
                continue
            vals = clean([d["as_auth_per_authed_ms"] for d in ds])
            if not vals:
                continue
            pts.append((statistics.mean([d["fleet"] for d in ds]), statistics.mean(vals),
                        ci95(vals)))
        pts.sort()
        axR.errorbar([p[0] for p in pts], [p[1] for p in pts], yerr=[p[2] for p in pts],
                     marker=mk, capsize=3, linewidth=1.8, label=lb)
    # Legend labels intentionally carry no citation numbers -- bibliography
    # numbering can change on recompilation; the reader maps names to refs
    # via the paper text and Table II.
    for cfg, lb, ls in (("CMP_HE2023", "He et al.", "-"),
                        ("CMP_HASSAN2022", "Hassan et al.", "-"),
                        ("CMP_SEIFELNASR2024", "Seifelnasr et al.", "-"),
                        ("CMP_BLS_BATCH", "batch verification (BLS)", "--")):
        vals = [d["as_auth_per_authed_ms"] for d in bl.get("c100_v50", {}).values()
                if d["config"] == cfg]
        if vals:
            axR.axhline(statistics.mean(vals), linewidth=1.2, linestyle=ls,
                        label=lb, alpha=0.85)
    axR.set_xlabel("fleet size (vehicles)")
    axR.set_ylabel("verifier cost per authenticated vehicle (ms)")
    style(axR)
    axR.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(figs, "scalability.png"), dpi=150)
    plt.close(fig)

    # ---------------- figure 2: latency with CIs ----------------
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.6, 3.4))
    scens = ["c20_v50", "c50_v50", "c100_v50", "c200_v50", "c500_v50"]
    fleets = [20, 50, 100, 200, 500]
    for key, mk, lb, sc in (("initial_latency_mean_ms", "o", "initial authentication", 1000.0),
                            ("reauth_latency_mean_ms", "s", "re-authentication", 1000.0),
                            ("join_time_mean_ms", "^", "end-to-end join time", 1000.0)):
        xs, ys, err = [], [], []
        for f, scen in zip(fleets, scens):
            ds = g.get(("O2M_AGG", scen), [])
            if not ds:
                continue
            vals = [d[key] / sc for d in ds]
            xs.append(f); ys.append(statistics.mean(vals)); err.append(ci95(vals))
        axL.errorbar(xs, ys, yerr=err, marker=mk, capsize=3, label=lb)
    axL.set_xscale("log")
    axL.set_xticks(fleets)
    axL.set_xticklabels([str(f) for f in fleets])
    axL.minorticks_off()
    axL.set_xlabel("fleet size (vehicles)")
    axL.set_ylabel("mean latency (s)")
    style(axL)
    axL.legend(fontsize=8, frameon=False)

    xs, ys, err = [], [], []
    for v in (30, 50, 80, 120):
        ds = g.get(("O2M_AGG", f"c100_v{v}"), [])
        if not ds:
            continue
        vals = [d["join_time_mean_ms"] / 1000.0 for d in ds]
        xs.append(v); ys.append(statistics.mean(vals)); err.append(ci95(vals))
    axR.errorbar(xs, ys, yerr=err, marker="o", capsize=3)
    axR.set_xticks([30, 50, 80, 120])
    axR.set_xlabel("nominal vehicle speed (km/h)")
    axR.set_ylabel("mean join time (s)")
    style(axR)
    fig.tight_layout()
    fig.savefig(os.path.join(figs, "latency.png"), dpi=150)
    plt.close(fig)

    # ---------------- figure 3: aggregated vs per-ciphertext decryption ------
    dec = load_dec_points()
    for cfg in ("O2M_AGG", "O2M_PAPER"):
        pts = dec.get(cfg, [])
        if pts:
            delays = sorted({round(p[1], 2) for p in pts})
            print(f"  decryption {cfg}: {len(pts)} points, d={min(p[0] for p in pts)}"
                  f"..{max(p[0] for p in pts)}, delays={delays[:3]}"
                  f"{'...' if len(delays) > 3 else ''}")
        else:
            print(f"  decryption {cfg}: NO DATA")
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    # aggregated: one flat line (the cost is the same for every window);
    # per-ciphertext: one dot per observed window.
    agg = sorted(dec.get("O2M_AGG", []))
    if agg:
        yagg = statistics.mean([p[1] for p in agg])
        ax.axhline(yagg, linewidth=1.8, color="#1f77b4",
                   label="aggregated (%.1f ms)" % yagg)
    per = sorted(dec.get("O2M_PAPER", []))
    if per:
        ax.plot([p[0] for p in per], [p[1] for p in per], marker="s",
                linestyle="none", markersize=4, alpha=0.6,
                color="#d62728", label="per-ciphertext")
    ax.set_xlabel("ciphertexts per aggregation window $d$")
    ax.set_ylabel("AS decryption delay (ms)")
    style(ax)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(figs, "decryption.png"), dpi=150)
    plt.close(fig)
    print("figures written to", figs)


if __name__ == "__main__":
    main()

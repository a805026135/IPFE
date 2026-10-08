#!/usr/bin/env python3
"""
Parse IPFEIA_LOG output of all simulation runs in results/ and produce
summary.csv plus evaluation figures.

Usage: python analyze.py [results_dir]
"""

import csv
import glob
import math
import os
import re
import sys
from collections import defaultdict

RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def percentile(values, p):
    if not values:
        return float("nan")
    values = sorted(values)
    k = (len(values) - 1) * p / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    return values[f] + (values[c] - values[f]) * (k - f)


def mean(values):
    return sum(values) / len(values) if values else float("nan")


CONFIG_NAMES = (
    "O2M_AGG",
    "O2M_PAPER",
    "O2O_AGG",
    "O2O_PAPER",
    "CMP_HE2023",
    "CMP_HASSAN2022",
    "CMP_SEIFELNASR2024",
    "CMP_BLS_BATCH",
)


class RunMetrics:
    def __init__(self, name):
        self.name = name
        self.veh_summary = []          # (id, authOk, authFail, ct, bytes, everAuthed)
        self.auth_ok_initial = []      # latency ms
        self.auth_ok_reauth = []
        self.join_time = []            # ms
        self.auth_fail = 0
        self.ct_total = 0
        self.as_delta = []             # (d, delay ms, mode)
        self.as_ack = []               # (resp, d)
        self.as_dec = []               # (d, n, delay ms, mode)
        self.as_summary = None
        self.rsu_summary = []          # (idx, aggCount, bytesSent, bytesRecv)
        self.rsu_agg = []              # (d, delay ms)
        self.chan_bytes = defaultdict(int)

    @property
    def config(self):
        for c in CONFIG_NAMES:
            if self.name.endswith("_" + c):
                return c
        return self.name.rsplit("_", 1)[1]

    @property
    def scenario(self):
        for c in CONFIG_NAMES:
            if self.name.endswith("_" + c):
                return self.name[: -(len(c) + 1)]
        return self.name.rsplit("_", 1)[0]

    def fleet(self):
        m = re.match(r"c(\d+)_v(\d+)", self.scenario)
        return int(m.group(1)) if m else 0

    def finish(self):
        n_veh = len(self.veh_summary)
        authed = sum(1 for v in self.veh_summary if v[5] == 1)
        auth_ok_total = sum(v[1] for v in self.veh_summary)
        # air-interface load = bytes actually transmitted (RSU + vehicle side);
        # received counters are not added to avoid double-counting each frame
        rsu_bytes = sum(v[2] for v in self.rsu_summary)
        veh_bytes = sum(v[4] for v in self.veh_summary)
        d = {
            "run": self.name,
            "scenario": self.scenario,
            "config": self.config,
            "fleet": self.fleet(),
            "vehicles": n_veh,
            "authed_vehicles": authed,
            "success_rate": authed / n_veh if n_veh else float("nan"),
            "auth_ok_total": auth_ok_total,
            "auth_fail_total": self.auth_fail,
            "initial_latency_mean_ms": mean(self.auth_ok_initial),
            "initial_latency_p95_ms": percentile(self.auth_ok_initial, 95),
            "reauth_latency_mean_ms": mean(self.auth_ok_reauth),
            "join_time_mean_ms": mean(self.join_time),
            "join_time_p95_ms": percentile(self.join_time, 95),
            "rsu_batches": len(self.rsu_agg),
            "rsu_batch_mean_d": mean([a[0] for a in self.rsu_agg]),
            "rsu_agg_delay_mean_ms": mean([a[1] for a in self.rsu_agg]),
            "as_batches": self.as_summary[3] if self.as_summary else 0,
            "as_auth_requests": self.as_summary[4] if self.as_summary else 0,
            "as_ack_total": self.as_summary[6] if self.as_summary else 0,
            "as_dec_msgs": self.as_summary[7] if self.as_summary else 0,
            "as_dec_vehicles": self.as_summary[8] if self.as_summary else 0,
            "as_dec_delay_mean_ms": mean([a[2] for a in self.as_dec]),
            "as_busy_s": (self.as_summary[10] / 1000.0) if self.as_summary else float("nan"),
            "as_auth_busy_ms": (
                self.as_summary[11] if self.as_summary and len(self.as_summary) > 11 else float("nan")
            ),
            "as_dec_busy_ms": (
                self.as_summary[12] if self.as_summary and len(self.as_summary) > 12 else float("nan")
            ),
        }
        d["as_busy_per_auth_ms"] = (
            d["as_busy_s"] * 1000 / d["as_auth_requests"] if d["as_auth_requests"] else float("nan")
        )
        # AS computation spent on authentication only, per authentication request
        d["as_auth_per_auth_ms"] = (
            d["as_auth_busy_ms"] / d["as_auth_requests"] if d["as_auth_requests"] else float("nan")
        )
        # AS authentication cost per *successfully authenticated* vehicle. In the
        # one-to-many mode one broadcast delta + one aggregate verification is
        # amortised over every vehicle that responds, so this is the quantity that
        # exposes the scalability of the broadcast design.
        d["as_auth_per_authed_ms"] = (
            d["as_auth_busy_ms"] / d["as_ack_total"] if d["as_ack_total"] else float("nan")
        )
        # average number of vehicles authenticated per broadcast delta
        d["vehicles_per_batch"] = (
            d["as_ack_total"] / d["as_batches"] if d["as_batches"] else float("nan")
        )
        d["total_bytes"] = rsu_bytes + veh_bytes
        d["channel_kbps"] = d["total_bytes"] * 8 / 300.0 / 1000.0
        return d


def parse_log(path):
    name = os.path.basename(path)[: -len(".log")]
    m = RunMetrics(name)
    with open(path, "r", errors="replace") as f:
        for line in f:
            if not line.startswith("IPFEIA_LOG,"):
                continue
            parts = line[len("IPFEIA_LOG,"):].strip().split(",")
            tag = parts[0]
            try:
                if tag == "VEH_SUMMARY":
                    m.veh_summary.append((parts[1], int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6])))
                elif tag == "AUTH_OK":
                    # AUTH_OK,<veh>,<t>,<latencyMs>,<round>,<initial|reauth>
                    lat = float(parts[3])
                    (m.auth_ok_initial if parts[5] == "initial" else m.auth_ok_reauth).append(lat)
                elif tag == "AUTH_FAIL":
                    m.auth_fail += 1
                elif tag == "JOIN_DONE":
                    # JOIN_DONE,<veh>,<t>,<joinMs>
                    m.join_time.append(float(parts[3]))
                elif tag == "RSU_SUMMARY":
                    m.rsu_summary.append((int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])))
                elif tag == "RSU_AGG":
                    # RSU_AGG,<rsu>,<t>,<d>,<n>,<aggMs>
                    m.rsu_agg.append((int(parts[3]), float(parts[5])))
                elif tag == "AS_DELTA":
                    m.as_delta.append((int(parts[3]), float(parts[4]), parts[5]))
                elif tag == "AS_ACK":
                    m.as_ack.append((int(parts[3]), int(parts[4])))
                elif tag == "AS_DEC":
                    m.as_dec.append((int(parts[2]), int(parts[3]), float(parts[4]), parts[5]))
                elif tag == "AS_SUMMARY":
                    # simtime, authMode, decMode, batches, authReq, resp, ack,
                    # decMsgs, decVehicles, decDelaySumMs, asBusyMs
                    m.as_summary = [
                        p if i in (1, 2) else (int(p) if 3 <= i <= 8 else float(p))
                        for i, p in enumerate(parts[1:])
                    ]
            except (IndexError, ValueError):
                continue
    return m


def main():
    logs = sorted(glob.glob(os.path.join(RESULTS, "*.log")))
    if not logs:
        print("No *.log files found in", RESULTS)
        return

    rows = []
    dec_points = defaultdict(list)  # (config, fleet) -> [(d, delay)]
    for path in logs:
        m = parse_log(path)
        rows.append(m.finish())
        # only the 50 km/h runs contribute to the summary figures; the c100_v30/
        # v80/v120 runs exist for the speed-sensitivity study and would otherwise
        # pile several points onto fleet = 100 and make the curves zig-zag
        if m.scenario.endswith("_v50"):
            for d, n, delay, mode in m.as_dec:
                dec_points[(m.config, m.fleet())].append((d, delay))

    rows.sort(key=lambda r: (r["config"], r["fleet"]))
    out_csv = os.path.join(RESULTS, "summary.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out_csv} ({len(rows)} runs)")
    for r in rows:
        print(
            "{run:24s} veh={vehicles:3d} succ={success_rate:5.1%} "
            "init={initial_latency_mean_ms:7.1f}ms join={join_time_mean_ms:7.1f}ms "
            "as/veh={as_auth_per_authed_ms:6.2f}ms batch={vehicles_per_batch:5.1f} "
            "chan={channel_kbps:7.1f}kbps".format(**r)
        )

    # NOTE: figures are produced by analyze_ci.py (mean +/- 95% CI over the
    # five seeds).  This script deliberately does NOT write any PNG: an
    # earlier version did, and its stale decryption.png silently shadowed
    # the CI figures in the paper directory.


if __name__ == "__main__":
    main()

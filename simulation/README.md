# Experiment code — Veins / OMNeT++ / SUMO simulation

Simulation-based evaluation of the IPFE-IA heterogeneous identity
authentication protocol in a realistic vehicular environment
(**Veins 5.2 + OMNeT++ 6.0.1 + SUMO 1.18.0**, coupled through TraCI).

This directory holds the code behind the *"Simulation Evaluation in a Realistic
Vehicular Environment"* section of the paper: the protocol modules, the scenario
generation, the experiment harnesses and the analysis scripts.

## Layout

```
simulation/
├── simenv.sh                  shared environment for Git Bash (PATH, SUMO, python)
├── build_all.sh               one-shot build of Veins + this project
├── make_real_scenario.py      OpenStreetMap extract -> Veins/SUMO scenario
├── clip_osm.py                clip an .osm to a lat/lon box
├── make_seed_variant.py       seed variants (<scenario>_s<k>) for the repeated runs
├── make_rsu_variant.py        15/35-RSU density variants
├── render_scenario.py         static rendering of a scenario
├── render_bg.py               campus-map background for the Qtenv screenshot
├── sumo/generate_scenario.py  synthetic Manhattan-grid scenario generator
├── launch_qtenv.sh            Qtenv GUI launcher (run-time screenshot, Fig. 9)
├── shaanxi_normal_yanta.osm   OSM extract used for the campus road network
├── crypto-bench/              jPBC 2.0.0 micro-benchmark of the primitives
├── analyze_ci.py              -> results/figs/*.png (mean ± 95 % CI over seeds)
├── plot_latency.py            latency-only plotting helper
├── _*.py, revision_*.sh       analysis helpers and the experiment queues that
│                              produced the revised (post-review) result set
└── veins-ipfeia/              the OMNeT++ project itself — see its README.md
```

## Dependencies

| Component | Version used | Role |
|---|---|---|
| OMNeT++ | 6.0.1 (Windows build, ships its own MinGW toolchain) | `opp_run`, `opp_makemake`, `opp_msgtool` |
| Veins | 5.2 | 802.11p / WAVE stack, `libveins.dll` |
| SUMO | 1.18.0 (`pip install eclipse-sumo`) | mobility, via `veins_launchd` + TraCI |
| Python | 3.x + `matplotlib` | `sumolib`, scenario generation, figures |
| Java | 11+ | only to re-run `crypto-bench/` (`java CryptoBenchmark.java`) |
| jPBC | 2.0.0 (jars vendored in `crypto-bench/libs/`) | pairing/group primitives |

The three large third-party trees are **not** part of this repository. Place
them either inside this directory (as in the authors' working tree) or next to
it — `simenv.sh` resolves both:

```
<work>/                         <work>/
├── omnetpp-6.0.1/              ├── simulation/
├── veins-src/                  │   ├── omnetpp-6.0.1/
├── venv/                       │   ├── veins-src/
└── simulation/                 │   ├── venv/
                                │   └── veins-ipfeia/
```

Override `OPP_ROOT`, `VEINS_SRC` or `VENV` to point anywhere else.

## Build

```sh
# inside an OMNeT++ shell (Windows: omnetpp-6.0.1/mingwenv.cmd; or source simenv.sh)

# 1) Veins
cd veins-src && ./configure && make MODE=release      # -> src/libveins.dll

# 2) this project
cd ../veins-ipfeia
./configure --with-veins=../veins-src                 # generates src/Makefile
make MODE=release                                     # -> src/libipfeia.dll

# 3) the jPBC micro-benchmark (only to re-measure the primitive unit costs)
cd ../crypto-bench
java -cp "libs/*" CryptoBenchmark.java a.properties results
```

`./build_all.sh` performs steps 1–2 for you inside an OMNeT++ shell.

## Scenarios

Scenarios are **generated**, so only the generators and the hand-written RSU
placements (`veins-ipfeia/scenarios/rsu_positions*.ini`) are versioned.

```sh
# campus scenario (the one used in the paper)
python make_real_scenario.py shaanxi_normal_yanta.osm c100_v50 \
       --bbox 108.9390,34.1980,108.9610,34.2145 --fleet 100 --rsus 25
python make_seed_variant.py          # -> c100_v50_s1 ... _s5 for every scenario
python make_rsu_variant.py           # -> rsu_positions_r15/r35.ini, omnetpp_r15/r35.ini
```

| Scenario | Fleet | Nominal speed |
|---|---|---|
| `c20_v50`, `c50_v50`, `c100_v50`, `c200_v50`, `c500_v50` | 20 / 50 / 100 / 200 / 500 | 50 km/h |
| `c100_v30`, `c100_v80`, `c100_v120` | 100 | 30 / 80 / 120 km/h |

Each has seed variants `_s1 … _s5` (same network, demand regenerated with a new
`randomTrips` seed) used for the repeated-runs study. The road network is the
Shaanxi Normal University Yanta campus and its surroundings
(≈ 2.0 km × 1.7 km of drivable roads) imported from OpenStreetMap, with 25 RSUs
placed at junctions by the grid-covering heuristic in `make_real_scenario.py`.

## Running

```sh
# one run:  ./run_sim.sh <Config> <scenario>
cd veins-ipfeia
./run_sim.sh O2M_AGG c100_v50_s1          # -> results/c100_v50_s1_O2M_AGG.log

# the full paper matrix (fleet scaling, speed sweep, mode comparison, baselines)
./run_all.sh

# short end-to-end smoke test
./run_smoke.sh
```

Useful environment overrides for `run_sim.sh`:

| Variable | Meaning |
|---|---|
| `OUTDIR` | where the log is written (default `veins-ipfeia/results`) |
| `INI` | alternative ini file (default `omnetpp.ini`) |
| `SUMO`, `PYTHON` | SUMO binary / python used to run `veins_launchd` |
| `LAUNCHD_PORT` | TraCI port (must be unique when running jobs in parallel) |

Parallel runs must also get a unique `--output-scalar-file`, see
`revision_finish.sh` for a worker-pool example.

## Analysis

```sh
# aggregated CSV of every run in results/
python veins-ipfeia/analyze.py

# paper figures: five-seed means with 95 % confidence intervals
python analyze_ci.py
```

`analyze_ci.py` is the **only** script that draws the paper figures
(`veins-ipfeia/results/figs/{scalability,latency,decryption}.png`); `analyze.py`
writes `summary.csv` only, so a stale plot cannot shadow a fresh one.

The repository ships the aggregated result table (`veins-ipfeia/results/summary.csv`)
and the three paper figures. The per-run logs (`results/*.log`) are not
versioned — regenerate them with `run_all.sh` and the `revision_*.sh` queues.

## Configuration reference (`veins-ipfeia/omnetpp.ini`)

| Config | AS authentication | AS decryption |
|---|---|---|
| `O2M_AGG` | one-to-many (broadcast delta + aggregate verify) | aggregated |
| `O2M_PAPER` | one-to-many | per-ciphertext |
| `O2O_AGG` | one-to-one (per vehicle) | aggregated |
| `O2O_PAPER` | one-to-one | per-ciphertext |
| `CMP_HE2023`, `CMP_HASSAN2022`, `CMP_SEIFELNASR2024` | one-to-one signature-based competitors | aggregated |
| `CMP_BLS_BATCH` | BLS-style batch/broadcast verification | aggregated |
| `GUI` | Qtenv, campus map as canvas background (screenshot only) | — |

Protocol and channel parameters:

| Parameter | Value |
|---|---|
| Key-extraction threshold `eta` / vector dimension `n` | 3 / 10 |
| Ciphertext reporting period | 5 s |
| Re-authentication period | 30 s |
| RSU aggregation window `aggWindow` | 5 s |
| AS batch / response window | 0.5 s / 0.8 s |
| RSU–AS backhaul one-way delay | 10 ms |
| Discrete-log decryption range `dlRange` | 2¹⁰ |
| PHY | 802.11p, 5.89 GHz, 10 MHz, 6 Mbit/s, 100 mW, −89 dBm sensitivity |
| Simulated time per run | 300 s |

Cryptographic operations are **not** instantaneous: every protocol step is
charged its measured jPBC cost, which advances the simulation clock, so
computation, transmission and waiting share one time axis.
`crypto-bench/` is the micro-benchmark that produced these unit costs
(E<sub>G1</sub> = 5.5002 ms, M<sub>G1</sub> = 0.0225 ms, BM = 2.7545 ms,
E<sub>T</sub> = 0.3145 ms, M<sub>Zq</sub> = 0.00021 ms, |G₁| = |G_T| = 128 B,
|Z_q| = 20 B), and they are hard-coded in `omnetpp.ini`.

## Log format

Each application prints CSV lines on stdout; grep for `IPFEIA_LOG,`:

```
KEY_GOT,<veh>,<t>,<rsu>,<keyCount>      AUTH_REQ,<veh>,<t>,<round>
DELTA_VERIFIED,<veh>,<t>,<round>        AUTH_OK,<veh>,<t>,<latencyMs>,<round>,<initial|reauth>
AUTH_FAIL,<veh>,<t>,timeout,<retries>   JOIN_DONE,<veh>,<t>,<joinMs>
CT,<veh>,<t>,<encMs>                    CHAN,<entity>,<t>,<bytesSent>,<bytesRecv>
RSU_AGG,<rsu>,<t>,<d>,<n>,<aggMs>       RSU_SUMMARY,<rsu>,<aggs>,<sentB>,<recvB>
AS_DELTA,<t>,<round>,<d>,<ms>,<o2m|o2o> AS_ACK,<t>,<round>,<resp>,<d>
AS_DEC,<t>,<d>,<n>,<ms>,<paper|aggregated>
AS_SUMMARY,...                          VEH_SUMMARY,<veh>,<ok>,<fail>,<ct>,<bytes>,<everAuthed>
```

## Methodology notes

* **Repetitions.** Every configuration of the proposed scheme is run with five
  independent random seeds; the seed drives both the SUMO demand and the
  channel/MAC randomness. Reported values are five-run means with 95 %
  Student-*t* confidence intervals. The signature-based competitors are
  deterministic once the measured primitive costs are fixed, and run once per
  fleet size.
* **Warm-up.** The demand is injected over the first 120 s of each 300 s run;
  excluding it changes the mean latencies by at most 0.27 s, well inside the
  reported intervals.
* **Propagation sensitivity.** The main results use the free-space exponent
  (α = 2) with a line-of-sight obstruction model. `omnetpp_alpha3.ini` and
  `omnetpp_alpha3_33dbm.ini` re-run the 100- and 500-vehicle scenarios with an
  urban empirical exponent (α = 3), at 20 dBm and at the 802.11p maximum of
  33 dBm respectively; `_alpha3.py` summarises the comparison.
* **Cost accounting.** The BLS batch baseline is charged one pairing per
  authenticated vehicle (the amortised cost of the *m* + 1-pairing batch test);
  the residual per-batch pairing and the verifier-side hash-to-G₁ are left
  uncharged, both of which favour that baseline.

## 中文说明

本目录是论文《One-to-Many Heterogeneous Identity Authentication for
Privacy-Preserving Vehicular Service Computing》仿真实验的完整代码：

* `veins-ipfeia/` 是 OMNeT++ 工程（协议模块 `src/`、配置 `omnetpp.ini`、运行脚本）；
* `make_real_scenario.py` 等由 OpenStreetMap 真实路网 + SUMO 生成车辆移动场景；
* `crypto-bench/` 是 jPBC 原语实测基准，其测得单价硬编码进仿真，使仿真中的
  密码运算按真实耗时推进仿真时钟；
* `analyze_ci.py` 汇总各次运行并按 5 个随机种子给出均值与 95% 置信区间，生成论文三张图。

运行前需自备三个第三方依赖树（OMNeT++ 6.0.1、Veins 5.2、装有 SUMO 的 Python venv），
放在本目录内或同级目录均可。构建：`./build_all.sh`；单次运行：
`cd veins-ipfeia && ./run_sim.sh O2M_AGG c100_v50`。

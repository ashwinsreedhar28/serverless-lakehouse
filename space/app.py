"""serverless-lakehouse — gold-layer dashboard as a Streamlit app (Hugging Face Space).

Reads data/gold.json, a snapshot of the gold tables written by `make dashboard` in the main repo. No Spark here:
the Space only draws what gold already says. Repo: https://github.com/ashwinsreedhar28/serverless-lakehouse
"""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).with_name("data") / "gold.json"
REPO = "https://github.com/ashwinsreedhar28/serverless-lakehouse"

# Validated categorical palette (blue, orange, aqua, yellow, magenta); engine identity is fixed, never cycled.
S = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
ENGINE_COLORS = {"emberserve": S[0], "worker-vllm": S[1]}

st.set_page_config(page_title="serverless-lakehouse", page_icon="🧊", layout="wide")


# --------------------------------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load() -> dict:
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    out = {"meta": raw["meta"]}
    for k, rows in raw.items():
        if k == "meta":
            continue
        df = pd.DataFrame(rows)
        for c in df.columns:
            if c.endswith("_utc") or c.startswith("t_"):      # ISO timestamps serialised by the exporter
                df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
        out[k] = df
    return out


def s_fmt(ms) -> str:
    if ms is None or pd.isna(ms):
        return "–"
    ms = float(ms)
    return f"{ms / 1000:.2f} s" if ms < 1000 else f"{ms / 1000:.1f} s" if ms < 300_000 else f"{ms / 1000:.0f} s"


def usd(v) -> str:
    if v is None or pd.isna(v):
        return "–"
    v = float(v)
    return f"${v:.4f}" if v < 0.01 else f"${v:.3f}" if v < 1 else f"${v:.2f}"


G = load()
M = G["meta"]
EV, BOOT, ENG = G["gold_coldstart_events"], G["gold_worker_boot_phases"], G["gold_engine_comparison"]
FB, SC, SW, COST = G["gold_flashboot_hit_rate"], G["gold_scoring_cost_per_batch"], G["gold_sweep_latency"], G["gold_cost_per_job"]
THR_S = M["flashboot_hit_ms"] / 1000


def eng_row(engine: str, weights: str, cohort: str | None = None) -> pd.Series:
    m = (ENG.engine == engine) & (ENG.weights_mode == weights)
    m &= (ENG.cohort == cohort) if cohort else (ENG.scope == "pooled")
    r = ENG[m]
    return r.iloc[0] if len(r) else pd.Series(dtype=object)


# --------------------------------------------------------------------------------------------------
# header + KPIs
# --------------------------------------------------------------------------------------------------

st.title("serverless-lakehouse")
st.caption(
    f"Gold layer of a bronze → silver → gold lakehouse over my own Runpod Serverless benchmark runs "
    f"(PySpark + Delta Lake). Built {M['built_at_utc']} · {len(EV)} cold starts · {len(BOOT)} worker boots · "
    f"{len(SW)} sweep runs · [repo]({REPO}) · every number traces to a landed source file."
)

eb, ef, wv = eng_row("emberserve", "baked"), eng_row("emberserve", "fetched"), eng_row("worker-vllm", "fetched")
wh = eng_row("worker-vllm", "fetched", "warm_host")
hits = int(EV.is_flashboot_hit.fillna(False).sum())
cache = BOOT[BOOT.torch_compile_s < 5]
nocache = BOOT[BOOT.torch_compile_s >= 5]
tiles = [
    ("Cold boot · emberserve, weights baked", s_fmt(eb.get("cold_delay_ms_p50")), f"pooled p50 of {eb.get('n_full_boots')} full boots"),
    ("Cold boot · emberserve, weights fetched", s_fmt(ef.get("cold_delay_ms_p50")), f"pooled p50 of {ef.get('n_full_boots')} full boots"),
    ("Cold boot · worker-vllm (pooled)", s_fmt(wv.get("cold_delay_ms_p50")),
     f"pooled p50 of {wv.get('n_full_boots')} · the two warm-host reruns alone: {s_fmt(wh.get('cold_delay_ms_mean'))} mean"),
    ("FlashBoot hits", f"{hits} / {len(EV)}", f"cold starts answered under {THR_S:.0f} s"),
    ("torch.compile, warm cache", f"{cache.torch_compile_s.median():.1f} s", f"vs {nocache.torch_compile_s.median():.0f} s cold · {len(cache)} of {len(BOOT)} boots"),
]
for col, (label, value, note) in zip(st.columns(5), tiles):
    col.metric(label, value)
    col.caption(note)
st.caption("Qwen3-8B on an RTX 4090 at $1.10/hr for the three cold-boot tiles. *Pooled* means every full boot of that engine, "
           "across hosts and eras; the engine table below splits the same boots by cohort.")

st.divider()

# --------------------------------------------------------------------------------------------------
# 1. cold-start dot plot
# --------------------------------------------------------------------------------------------------

st.subheader("Every cold start, by engine and where the weights came from")
st.caption(f"One dot per successful cold-labelled request. Hollow dots were answered in under {THR_S:.0f} s: a FlashBoot resume "
           "or a worker that was still warm. The tick is the lane's median. Log scale.")
f1, f2, f3 = st.columns(3)
engines = f1.multiselect("Engine", sorted(EV.engine.unique()), default=sorted(EV.engine.unique()))
models = f2.multiselect("Model", sorted(EV.model.unique()), default=sorted(EV.model.unique()))
gpus = f3.multiselect("GPU", sorted(EV.gpu_model.unique()), default=sorted(EV.gpu_model.unique()))
ev = EV[EV.engine.isin(engines) & EV.model.isin(models) & EV.gpu_model.isin(gpus)].copy()
ev["lane"] = ev.engine + " · " + ev.weights_mode
ev["delay_s"] = ev.delay_ms / 1000
ev["hit"] = ev.is_flashboot_hit.fillna(False).map({True: "FlashBoot hit", False: "full boot"})
ev["when"] = ev.request_ts_utc.dt.strftime("%Y-%m-%d").fillna("–") if "request_ts_utc" in ev else "–"
lane_order = [l for l in ["emberserve · baked", "emberserve · fetched", "worker-vllm · fetched", "worker-vllm · volume"] if l in set(ev.lane)]
if len(ev):
    base = alt.Chart(ev).encode(
        y=alt.Y("lane:N", sort=lane_order, title=None, axis=alt.Axis(labelFontWeight="bold", labelLimit=220)),
        x=alt.X("delay_s:Q", scale=alt.Scale(type="log"), title="delay before the job ran (s, log)"),
        color=alt.Color("engine:N", scale=alt.Scale(domain=list(ENGINE_COLORS), range=list(ENGINE_COLORS.values())), legend=alt.Legend(title="engine", orient="top")),
        tooltip=[alt.Tooltip("series_label:N", title="series"), alt.Tooltip("endpoint_id:N", title="endpoint"), "model:N",
                 alt.Tooltip("gpu_model:N", title="GPU"), alt.Tooltip("weights_mode:N", title="weights"), alt.Tooltip("host_state:N", title="host"),
                 alt.Tooltip("delay_s:Q", title="delay (s)", format=".1f"), alt.Tooltip("exec_ms:Q", title="exec (ms)"),
                 "hit:N", alt.Tooltip("est_cost_usd:Q", title="est. $", format=".4f"), alt.Tooltip("when:N", title="date")],
    )
    full = base.transform_filter(alt.datum.hit == "full boot").mark_circle(size=90, opacity=0.9, stroke="white", strokeWidth=1).encode(
        yOffset=alt.YOffset("jitter:Q", scale=alt.Scale(domain=[-1, 1], range=[-12, 12]))).transform_calculate(jitter="(random() - 0.5) * 2")
    hollow = base.transform_filter(alt.datum.hit == "FlashBoot hit").mark_point(size=110, filled=False, strokeWidth=2.2)
    med = alt.Chart(ev).mark_tick(color="#1b2128", thickness=2.5, size=34).encode(
        y=alt.Y("lane:N", sort=lane_order), x=alt.X("median(delay_s):Q"),
        tooltip=[alt.Tooltip("lane:N"), alt.Tooltip("median(delay_s):Q", title="median delay (s)", format=".1f"), alt.Tooltip("count():Q", title="n")])
    st.altair_chart((full + hollow + med).properties(height=90 + 64 * len(lane_order)), width="stretch")
    with st.expander("Table view"):
        st.dataframe(ev[["engine", "weights_mode", "model", "gpu_model", "host_state", "series_label", "endpoint_id", "when",
                         "delay_ms", "exec_ms", "hit", "est_cost_usd"]],
                     hide_index=True, width="stretch",
                     column_config={"est_cost_usd": st.column_config.NumberColumn("est. $", format="$%.4f"),
                                    "delay_ms": st.column_config.NumberColumn("delay (ms)", format="%d"),
                                    "exec_ms": st.column_config.NumberColumn("exec (ms)", format="%d")})
else:
    st.info("No cold starts match the filters.")

st.divider()

# --------------------------------------------------------------------------------------------------
# 2. worker-vllm boot anatomy
# --------------------------------------------------------------------------------------------------

st.subheader("Where worker-vllm's boot seconds go")
b = BOOT[BOOT.start_to_api_ready_s.notna() & BOOT.start_to_weights_s.notna()].copy()
n_unanchored = len(BOOT) - len(b)
st.caption("From vLLM's own log lines: weights downloaded and loaded, `torch.compile`, CUDA-graph capture (summed over its passes — "
           "vLLM 0.30 does two), the rest of engine init, then the API server coming up. One bar per boot, sorted by total. "
           f"Two boots hit a warm compile cache. {n_unanchored} of {len(BOOT)} boots have no `vllm serve` line in their export "
           "(the console missed it, or the log starts mid-boot), so their wall-clock bar cannot be drawn; they are in the table "
           "below with their per-phase seconds.")
PH = [("download + load weights", S[0]), ("torch.compile", S[1]), ("CUDA-graph capture", S[2]), ("rest of engine init", S[3]), ("to 'startup complete'", S[4])]
b["name"] = (b.source_file.str.replace(r"^.*/", "", regex=True).str.replace(r"\.(log|txt)$", "", regex=True)
             .str.replace(r"_worker(_log)?", "", regex=True).str.replace(r"^serverless_coldstart_", "", regex=True)
             .str.replace(r"^endpoint_logs_1450-1553_", "", regex=True))
b.loc[b.boot_index > 1, "name"] = b.name + " · boot " + b.boot_index.astype(str)
b["cache_hit"] = b.torch_compile_s < 5
comp, gr, init = b.torch_compile_s.fillna(0), b.graph_capture_s.fillna(0), b.init_engine_s.fillna(0)
seg = pd.DataFrame({
    "name": b.name, "total": b.start_to_api_ready_s, "cache_hit": b.cache_hit, "vllm_version": b.vllm_version,
    PH[0][0]: b.start_to_weights_s, PH[1][0]: comp, PH[2][0]: gr,
    PH[3][0]: (init - comp - gr).clip(lower=0), PH[4][0]: (b.start_to_api_ready_s - b.start_to_weights_s - init).clip(lower=0),
})
long = seg.melt(id_vars=["name", "total", "cache_hit", "vllm_version"], var_name="phase", value_name="seconds")
long["phase_order"] = long.phase.map({p: i for i, (p, _) in enumerate(PH)})
order = seg.sort_values("total", ascending=False).name.tolist()
bars = alt.Chart(long).mark_bar(cornerRadius=2).encode(
    y=alt.Y("name:N", sort=order, title=None, axis=alt.Axis(labelLimit=320)),
    x=alt.X("seconds:Q", stack="zero", title="seconds since `vllm serve` started"),
    color=alt.Color("phase:N", scale=alt.Scale(domain=[p for p, _ in PH], range=[c for _, c in PH]), legend=alt.Legend(orient="top", title=None)),
    order=alt.Order("phase_order:Q"),
    tooltip=["name:N", alt.Tooltip("vllm_version:N", title="vLLM"), "phase:N", alt.Tooltip("seconds:Q", format=".1f"), alt.Tooltip("total:Q", title="total to API ready (s)", format=".0f")],
)
labels = alt.Chart(seg).mark_text(align="left", dx=6, color="#1b2128").encode(
    y=alt.Y("name:N", sort=order), x=alt.X("total:Q"),
    text=alt.Text("label:N")).transform_calculate(label="format(datum.total, '.0f') + ' s' + (datum.cache_hit ? '  · compile cache hit' : '')")
st.altair_chart((bars + labels).properties(height=40 + 30 * len(seg)), width="stretch")
with st.expander("Table view"):
    st.dataframe(BOOT[["source_file", "boot_index", "worker_id", "segmented_by", "vllm_version", "start_to_weights_s", "weights_load_s",
                       "torch_compile_s", "graph_capture_s", "n_graph_passes", "init_engine_s", "start_to_api_ready_s",
                       "api_ready_to_first_job_s", "kv_cache_gib"]],
                 hide_index=True, width="stretch")

st.divider()

# --------------------------------------------------------------------------------------------------
# 3. engine comparison + FlashBoot
# --------------------------------------------------------------------------------------------------

c1, c2 = st.columns([1.15, 1])
with c1:
    st.subheader("Same GPU, same model: the engines side by side")
    st.caption("Qwen3-8B on an RTX 4090, full boots only (FlashBoot hits excluded). **pooled** rows mix every run; the cohort rows "
               "beneath split them by host state and data era, so a pooled median is never quoted alone. The two warm-host "
               "worker-vllm samples are the pair behind the 147.5 s in the Sep 30 write-up.")
    e = ENG.copy()
    e["engine · weights"] = e.apply(lambda r: f"{r.engine} · {r.weights_mode}" if r.scope == "pooled" else "", axis=1)
    e["cohort"] = e.apply(lambda r: "all runs (pooled)" if r.scope == "pooled" else "    ↳ " + str(r.cohort).replace("_", " "), axis=1)
    e["dates"] = e.dates.apply(lambda d: ", ".join(d) if isinstance(d, list) else "")
    st.dataframe(e[["engine · weights", "cohort", "n_full_boots", "n_undated", "cold_delay_ms_p50", "cold_delay_ms_mean", "cold_delay_ms_min",
                    "cold_delay_ms_max", "cold_est_cost_usd_p50", "n_warm", "warm_exec_ms_p50", "dates"]],
                 hide_index=True, width="stretch",
                 column_config={"n_full_boots": st.column_config.NumberColumn("full boots"),
                                "n_undated": st.column_config.NumberColumn("undated", help="boots whose file carries no wall-clock timestamp; `dates` covers the rest"),
                                "cold_delay_ms_p50": st.column_config.NumberColumn("cold p50 (ms)", format="%d"),
                                "cold_delay_ms_mean": st.column_config.NumberColumn("cold mean (ms)", format="%d"),
                                "cold_delay_ms_min": st.column_config.NumberColumn("min (ms)", format="%d"),
                                "cold_delay_ms_max": st.column_config.NumberColumn("max (ms)", format="%d"),
                                "cold_est_cost_usd_p50": st.column_config.NumberColumn("$ / cold start", format="$%.4f"),
                                "n_warm": st.column_config.NumberColumn("warm n"),
                                "warm_exec_ms_p50": st.column_config.NumberColumn("warm exec p50 (ms)", format="%d")})
with c2:
    st.subheader("Fast cold responses (FlashBoot proxy)")
    st.caption(f"Share of *successful* cold-labelled requests answered in under {THR_S:.0f} s, per endpoint and setting. The data "
               "cannot tell a FlashBoot resume from a worker that was still warm, so this is a proxy, named for what it measures. "
               "`failed` counts the cold attempts the denominator leaves out, so a 100 % on one boot reads as 1-of-1-after-N-failures.")
    st.dataframe(FB[["engine", "model", "endpoint_id", "flashboot_setting", "n_cold", "n_cold_failed", "n_hits", "n_resume_recorded",
                     "hit_rate", "hit_delay_ms_p50", "miss_delay_ms_p50"]],
                 hide_index=True, width="stretch",
                 column_config={"hit_rate": st.column_config.ProgressColumn("fast-response rate", min_value=0, max_value=1, format="percent"),
                                "flashboot_setting": "setting", "n_cold": "cold", "n_cold_failed": "failed", "n_hits": "hits",
                                "n_resume_recorded": st.column_config.NumberColumn("engine flag", help="requests where the engine itself wrote flashboot_resume=true (1 of 13 series files records it)"),
                                "hit_delay_ms_p50": st.column_config.NumberColumn("hit p50 (ms)", format="%d"),
                                "miss_delay_ms_p50": st.column_config.NumberColumn("miss p50 (ms)", format="%d")})

st.divider()

# --------------------------------------------------------------------------------------------------
# 4. cost
# --------------------------------------------------------------------------------------------------

c3, c4 = st.columns(2)
with c3:
    st.subheader("$ per cold start (request-duration proxy)")
    st.caption("Median of (delay + exec) × $/hr, Qwen3-8B on an RTX 4090 at $1.10/hr, pooled. A comparison metric, not billed time: "
               "Runpod bills worker start, execution and idle per worker, which a per-request sum neither bounds above nor below.")
    cc = ENG[(ENG.scope == "pooled") & ENG.cold_est_cost_usd_p50.notna()].copy()
    cc["label"] = cc.engine + " · " + cc.weights_mode
    ch = alt.Chart(cc).mark_bar(cornerRadius=3).encode(
        y=alt.Y("label:N", sort="x", title=None), x=alt.X("cold_est_cost_usd_p50:Q", title="$ per full cold start (p50)", axis=alt.Axis(format="$.3f")),
        color=alt.Color("engine:N", scale=alt.Scale(domain=list(ENGINE_COLORS), range=list(ENGINE_COLORS.values())), legend=None),
        tooltip=["label:N", alt.Tooltip("cold_est_cost_usd_p50:Q", title="$ / cold start", format="$.4f"), alt.Tooltip("n_full_boots:Q", title="boots"),
                 alt.Tooltip("cold_delay_ms_p50:Q", title="cold p50 (ms)")])
    txt = ch.mark_text(align="left", dx=5, color="#1b2128").encode(text=alt.Text("cold_est_cost_usd_p50:Q", format="$.4f"))
    st.altair_chart((ch + txt).properties(height=150), width="stretch")
with c4:
    st.subheader("$ per 1,000 scored articles")
    st.caption("The Pulse scoring job, 50 articles per batch, cost from each backend's own price table. Local ollama runs have no price and are omitted.")
    sc = SC[SC.est_cost_usd_per_1k_articles.notna()].copy()
    sc["label"] = (sc.model.str.replace(r"^.*/", "", regex=True).str.replace(r"-\d{8}$", "", regex=True)
                   + sc.label.fillna("").map(lambda l: "" if not l else " · " + l.replace("prefixcache-on", "prefix on").replace("q32awq-prefix", "prefix on"))
                   + sc.concurrency.map(lambda c: f" · c{c}" if c and c > 1 else "")
                   + sc.apply(lambda r: f" · {r.gpu_model}" if r.backend == "runpod" and isinstance(r.gpu_model, str) else "", axis=1))
    ch2 = alt.Chart(sc).mark_bar(cornerRadius=3, color=S[0]).encode(
        y=alt.Y("label:N", sort="x", title=None, axis=alt.Axis(labelLimit=260)),
        x=alt.X("est_cost_usd_per_1k_articles:Q", title="$ per 1,000 articles", axis=alt.Axis(format="$.2f")),
        tooltip=["backend:N", "model:N", "label:N", alt.Tooltip("est_cost_usd_per_1k_articles:Q", title="$ / 1k", format="$.3f"),
                 alt.Tooltip("wall_s_per_article:Q", title="s / article", format=".2f"), alt.Tooltip("mean_score:Q", title="mean score"),
                 alt.Tooltip("parse_ok_rate:Q", title="parse ok", format=".0%")])
    txt2 = ch2.mark_text(align="left", dx=5, color="#1b2128").encode(text=alt.Text("est_cost_usd_per_1k_articles:Q", format="$.3f"))
    st.altair_chart((ch2 + txt2).properties(height=30 * len(sc) + 20), width="stretch")
    low = SC[SC.parse_ok_rate < 0.9]
    if len(low):
        st.caption("Parse-ok below 90%: " + "; ".join(f"{r.model.split('/')[-1]} ({r.parse_ok_rate:.0%}{', ' + r.label if isinstance(r.label, str) else ''})" for r in low.itertuples())
                   + " — cheap tokens that did not return the JSON asked for.")

st.divider()

# --------------------------------------------------------------------------------------------------
# 5. sweeps
# --------------------------------------------------------------------------------------------------

st.subheader("Time to first token under load")
st.caption("Median TTFT per request rate for each emberserve Serverless sweep. ∞ = unpaced: all 200 requests queued at t=0, capped by "
           "max_concurrency where the run set one (hover a point). Systems differ in model size — `7b_…` is Qwen2.5-7B, `emberserve`/`emberserve_v2` "
           "ran on the Qwen2.5-0.5B endpoint — and in endpoint mode: queue endpoints add a hop and a worker pool, the load balancer talks to the server directly.")
sw = SW[SW.ttft_ms_p50.notna() & (SW.completed > 0)].copy()
sw["rate"] = sw.request_rate.map(lambda r: "∞" if r == "inf" else f"{float(r):g}")
sw = sw.drop(columns=["request_rate"])   # mixed float/"inf" column cannot be serialised to Arrow for the chart
sw["short"] = sw.system.str.replace("^runpod_serverless_", "", regex=True).str.replace("pagedserve", "emberserve") + sw.endpoint_mode.map({"queue": " (queue)", "load_balancer": " (load balancer)"})
keep = sw.groupby("short").size()
sw = sw[sw.short.isin(keep[keep >= 3].index)]
sw["ttft_s"] = sw.ttft_ms_p50 / 1000
systems = sorted(sw.short.unique())
line = alt.Chart(sw).mark_line(point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=2).encode(
    x=alt.X("rate:N", sort=["1", "2", "4", "8", "16", "∞"], title="offered request rate (req/s)"),
    y=alt.Y("ttft_s:Q", scale=alt.Scale(type="log"), title="TTFT p50 (s, log)"),
    color=alt.Color("short:N", scale=alt.Scale(domain=systems, range=S[:len(systems)]), legend=alt.Legend(orient="top", title=None, columns=3)),
    tooltip=["short:N", "rate:N", alt.Tooltip("ttft_ms_p50:Q", title="TTFT p50 (ms)", format=".0f"), alt.Tooltip("ttft_ms_p99:Q", title="TTFT p99 (ms)", format=".0f"),
             alt.Tooltip("e2e_ms_p99:Q", title="e2e p99 (ms)", format=".0f"), alt.Tooltip("completed:Q", title="ok"), alt.Tooltip("failed:Q", title="failed"),
             alt.Tooltip("output_tok_s:Q", title="out tok/s", format=".0f"), alt.Tooltip("max_concurrency:Q", title="max conc.")],
)
st.altair_chart(line.properties(height=380), width="stretch")
with st.expander("Table view"):
    swt = SW.assign(request_rate=SW.request_rate.map(lambda r: "∞" if r == "inf" else f"{float(r):g}"))  # one dtype for Arrow
    st.dataframe(swt[["system", "endpoint_mode", "request_rate", "max_concurrency", "completed", "failed", "requests_per_s", "output_tok_s",
                      "ttft_ms_p50", "ttft_ms_p99", "e2e_ms_p50", "e2e_ms_p99"]], hide_index=True, width="stretch")

st.divider()
st.caption(f"Method, schemas and the design decisions: [README]({REPO}#readme). The same gold tables as markdown: "
           f"[docs/gold_report.md]({REPO}/blob/main/docs/gold_report.md). Medians are Spark `percentile_approx` (an observed value, no "
           "interpolation). Costs are a request-duration proxy with the formula stated; fast cold responses are a threshold proxy for FlashBoot, "
           "not Runpod's own accounting; cohorts are observational, not a controlled experiment.")

---
license: mit
pretty_name: Runpod Serverless LLM benchmarks — cold starts, worker logs, load sweeps, scoring runs
language:
  - en
tags:
  - benchmark
  - llm-inference
  - serverless
  - gpu
  - cold-start
  - vllm
  - runpod
  - data-engineering
  - lakehouse
size_categories:
  - 10K<n<100K
configs:
  - config_name: pulse_coldstart_requests
    data_files: landing/pulse/results.csv
    default: true
  - config_name: pulse_throughput_requests
    data_files: landing/pulse/results_throughput.csv
  - config_name: pulse_quality_requests
    data_files: landing/pulse/bench/quality.csv
  - config_name: pulse_quality_batches
    data_files: landing/pulse/bench/quality_batches.csv
---

# Runpod Serverless LLM benchmarks

Raw benchmark output from running LLM inference on [Runpod Serverless](https://www.runpod.io/serverless-gpu)
between 2026-09-23 and 2026-10-01: cold-start timelines, load sweeps, per-request latencies, the workers' own
boot logs, and an LLM scoring job run against several backends. Two engines appear on the same GPU and model —
[emberserve](https://github.com/ashwinsreedhar28/emberserve) (my from-scratch inference engine, formerly
*pagedserve*) and Runpod's `worker-vllm` — which is what makes the data worth keeping.

This is the **landing zone** of [serverless-lakehouse](https://github.com/ashwinsreedhar28/serverless-lakehouse),
a bronze → silver → gold pipeline (local PySpark + Delta Lake) whose gold layer is served as a
[Space](https://huggingface.co/spaces/ashwin-sreedhar/serverless-lakehouse). The files here are byte-identical
to `data/landing/` in that repository: every table, chart and headline number in the pipeline is reproducible
from this dataset alone with `make bronze && make silver && make gold`.

## What is in it

| folder / file | files | format | one record is |
|---|---|---|---|
| `landing/emberserve/results/serverless_coldstart_*.json` | 13 | JSON (one object per series) | a cold-start **series**: `runs[]` of {cold request, warm request, worker health before}, with `delay_ms` / `execution_ms` / `worker_id` per request and, where the engine wrote them, `phases_s` and a `timeline` |
| `landing/emberserve/results/runpod_serverless_*.json` | 10 | JSON | a load **sweep**: `runs[]` per request rate (1 → ∞) with summary latencies; four files also carry per-request `records[]` (arrival, first token, finish) |
| `landing/pulse/results.csv` (+ `results_v0.csv`, `bench/logs/results_runs1-3.csv`) | 3 | CSV | one cold-start **request** from the Pulse `coldstart.py` harness: endpoint, typed GPU label, kind (cold/warm), cycle, `delay_ms`, `exec_ms`, status, tokens, `workers_before` JSON. `results_v0.csv` is an earlier 15-column layout of the same runs 1–3 |
| `landing/pulse/results_throughput.csv` | 1 | CSV | one request of a prefix-cache on/off throughput run |
| `landing/pulse/bench/quality.csv`, `quality_batches.csv` | 2 | CSV | one scored article / one 50-article batch of the Pulse scoring job across Runpod (Qwen3-8B, Qwen3-32B-AWQ), Claude, OpenRouter and Ollama backends, with the price table used |
| `landing/pulse/bench/logs/*.log`, `landing/emberserve/results/*_worker_log.txt` | 18 | text | a worker's console export: vLLM's own boot lines (`Loading weights took …`, `torch.compile took …`, `Graph capturing finished in …`, `init engine … took …`, `Application startup complete`), in three timestamp formats |
| `landing/manifest.json` | 1 | JSON | provenance: source root, `sha256` of the source and of the landed copy, byte count, redaction count and dataset tag for every file |
| `gold/gold_report.md`, `gold/gold.json` | 2 | Markdown / JSON | the derived gold tables as of the commit that published this dataset — the same snapshot the Space renders |

The four CSVs are exposed as viewer configs; the JSON and log files are raw and are read by the pipeline's
bronze step (`lakehouse/bronze.py`), which keeps one row per `runs[]` / `records[]` element and leaves nested
objects as JSON strings.

Hardware in the data: RTX 4090 (24 GB PRO tier), A40 and RTX A6000 (48 GB tier), A100 and H100 with a network
volume, and one unidentified 24 GB-tier card. Models: Qwen3-8B (most runs), Qwen3-32B-AWQ, Qwen2.5-0.5B and
Qwen2.5-7B.

## Things to know before using it

- **Observational, not controlled.** Cohorts differ in engine build, host state (fresh host pulling the image vs.
  same-night rerun), date and endpoint settings. Pooled medians across cohorts are labelled *pooled* in the
  pipeline for that reason.
- **A GPU label is what the operator typed, not where Runpod placed the job.** `gpu` in the Pulse CSVs is a
  command-line argument; run 7 on endpoint `4ib59mjp0vgaao` carried the 24 GB PRO label but ran on an A40 (its
  worker boot is in `endpoint_logs_1450-1553_4090_and_A40.log`). The pipeline corrects it with a seed row; the
  raw files are left as written.
- **Timestamps.** CSV `ts_utc` is ISO-8601 UTC. Worker logs mix three formats: console exports in
  `GMT-0400`, API-style ISO `Z`, and one laptop-local export in `America/New_York` whose lines also carry the
  wrapper's own UTC stamp.
- **FlashBoot.** Only one series file records the engine's `flashboot_resume` flag; elsewhere a "fast cold
  response" is a proxy (successful cold-labelled request under 5 s) and cannot be told from a worker that was
  still warm.
- **Not here:** the Pulse `quality_*.log` files, `.env`, server-side logs and the article fixture.

## Redaction and provenance

Every file passed through `lakehouse/land.py`, which copies source bytes through one credential-pattern list
(HF / Runpod / OpenAI-style keys, GitHub and Slack tokens, AWS keys, PEM blocks, JWTs, `Bearer`/`Basic` auth,
`key=value` secrets) and records what it removed in `manifest.json`. `redactions_total` is 0: the sources were
already clean — the `api_key` field in sweep `args` is `"<redacted>"` at source. Endpoint IDs and worker IDs are
kept; they are not credentials (every call needs a bearer key) and are already public in the emberserve repo.

`manifest.json` lets you verify any file: `sha256sum landing/<path>` must equal that file's `sha256_landed`.

## License and citation

MIT, same as the pipeline. If you use it:

```
Sreedhar, A. (2026). Runpod Serverless LLM benchmarks: cold starts, worker logs, load sweeps, scoring runs.
https://huggingface.co/datasets/ashwin-sreedhar/runpod-serverless-benchmarks
```

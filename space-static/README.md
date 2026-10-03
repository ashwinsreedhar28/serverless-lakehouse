---
title: serverless-lakehouse
emoji: 🧊
colorFrom: blue
colorTo: gray
sdk: static
pinned: false
license: mit
short_description: Gold-layer dashboard of a PySpark + Delta lakehouse over Runpod Serverless benchmarks
---

# serverless-lakehouse — dashboard

The gold layer of a bronze → silver → gold lakehouse built with local PySpark + Delta Lake over my own Runpod
Serverless benchmark runs: cold starts by engine, GPU and where the weights came from; worker-vllm's boot anatomy
from its own log lines; FlashBoot hit rate; estimated cost per job; emberserve vs worker-vllm on the same GPU.

This Space is one static HTML file. `index.html` is `docs/dashboard.html` from the main repository: the gold
tables embedded as JSON by `make dashboard`, with the charts drawn in the browser as SVG. Nothing here computes a
metric; the page shows what the tables say. Pipeline, schemas and design decisions:
https://github.com/ashwinsreedhar28/serverless-lakehouse

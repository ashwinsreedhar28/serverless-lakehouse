---
title: serverless-lakehouse
emoji: 🧊
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Gold-layer dashboard of a PySpark + Delta lakehouse over Runpod Serverless benchmarks
---

# serverless-lakehouse — dashboard

The gold layer of a bronze → silver → gold lakehouse built with local PySpark + Delta Lake over my own Runpod
Serverless benchmark runs: cold starts by engine, GPU and where the weights came from; worker-vllm's boot anatomy
from its own log lines; FlashBoot hit rate; estimated cost per job; emberserve vs worker-vllm on the same GPU.

This Space has no Spark in it. `data/gold.json` is a snapshot of the gold tables written by `make dashboard` in
the main repository, and `app.py` only draws what those tables say. Pipeline, schemas and design decisions:
https://github.com/ashwinsreedhar28/serverless-lakehouse

---
title: serverless-lakehouse
emoji: 🧊
colorFrom: blue
colorTo: gray
sdk: static
pinned: false
license: mit
short_description: Lakehouse over Runpod Serverless runs, on Spark/Delta and on Snowflake/dbt
---

# serverless-lakehouse — dashboard

The gold layer of a bronze → silver → gold lakehouse over my own Runpod Serverless runs, built twice — local PySpark +
Delta Lake, and Snowflake + dbt Core — with a parity check that shows the two agree. Cold starts by engine, GPU and where
the weights came from; worker-vllm's boot anatomy from its own log lines; FlashBoot hit rate; estimated cost per job;
emberserve vs worker-vllm on the same GPU. Then the live part: a measurement campaign of 24 cells (4 GPUs × FlashBoot
off/on × 3 images, ten cold starts each) with the placement-vs-boot split, FlashBoot off → on per GPU, $ per cold start,
and the Runpod account as its API reports it day by day.

This Space is one static HTML file. `index.html` is `docs/dashboard.html` from the main repository: the gold tables
embedded as JSON by `make dashboard` (Spark) or `make sf-dashboard` (Snowflake — the meta line says which), with the
charts drawn in the browser as SVG. Nothing here computes a metric; the page shows what the tables say. Pipeline,
schemas, the spend log and design decisions: https://github.com/ashwinsreedhar28/serverless-lakehouse

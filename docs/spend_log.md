# Spend log

Actual $ from Runpod's `GET /v2/billing/serverless` (hourly buckets, via the poller; polls 2026-10-07 22:28:14 → 2026-10-08 16:35:11 UTC). Estimates from `campaign/runs.csv` and 0.013 $/run for the load generator. Rule: stop when an endpoint's actual exceeds its estimate by 20%. Generated 2026-10-08 16:35 UTC.

## Per endpoint

| endpoint | name | estimated $ | actual $ | acknowledged $ | ratio (actual − ack) / est | status |
|---|---|---|---|---|---|---|
| 74ulbugzbbba8o |  | 0.0000 | 0.1069 | 0.0000 | — | — |
| h90byyjfb0ofbu | pagedserve0929z | 0.2120 | 0.8956 | 0.7000 | 0.92 | ok |
| nfr1cqjnqikgwm | pagedserve | 0.0000 | 0.0131 | 0.0000 | — | — |
| ri6eo614hmu510 | pagedserve0929x | 0.7132 | 0.4484 | 0.0000 | 0.63 | ok |
| rvy2p7bfia91fm | pagedserve0929 | 1.8150 | 1.6712 | 0.0000 | 0.92 | ok |

**Total actual: $3.1352** · total estimated: $2.7402

## Per endpoint per day (actual)

| day (UTC) | endpoint | name | total $ | gpu $ | billed hours |
|---|---|---|---|---|---|
| 2026-10-06 | 74ulbugzbbba8o |  | 0.1069 | 0.1067 | 2 |
| 2026-10-08 | h90byyjfb0ofbu | pagedserve0929z | 0.8956 | 0.8952 | 4 |
| 2026-10-08 | nfr1cqjnqikgwm | pagedserve | 0.0131 | 0.0131 | 1 |
| 2026-10-08 | ri6eo614hmu510 | pagedserve0929x | 0.4484 | 0.4475 | 3 |
| 2026-10-08 | rvy2p7bfia91fm | pagedserve0929 | 1.6712 | 1.6538 | 5 |

## What ran (campaign/runs.csv)

| date (UTC) | cell | endpoint | n_cold | est $ | note |
|---|---|---|---|---|---|
| 20261008T0249Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 621.3 s (min 621.3, max 621.3), delayTime median 617980 ms, warm 999 ms, failu |
| 20261008T0402Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 441.2 s (min 441.2, max 441.2), delayTime median 438489 ms, warm 954 ms, failu |
| 20261008T0402Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 83.6 s (min 83.6, max 83.6), delayTime median 80849 ms, warm 555 ms, failures 0 |
| 20261008T0402Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 213.6 s (min 213.6, max 213.6), delayTime median 211287 ms, warm 1099 ms, failu |
| 20261008T0402Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 482.6 s (min 482.6, max 482.6), delayTime median 478817 ms, warm 745 ms, failure |
| 20261008T0402Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 725.2 s (min 725.2, max 725.2), delayTime median 722555 ms, warm 2124 ms, fail |
| 20261008T0402Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 19.2 s (min 19.2, max 19.2), delayTime median 16490 ms, warm 604 ms, failures 0 |
| 20261008T0402Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 766.7 s (min 766.7, max 766.7), delayTime median 763781 ms, warm 1396 ms, fail |
| 20261008T0402Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 108.9 s (min 108.9, max 108.9), delayTime median 106235 ms, warm 1352 ms, failu |
| 20261008T0402Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median - s (min -, max -), delayTime median None ms, warm 625809 ms, failures 1, no |
| 20261008T0402Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median 16.9 s (min 16.9, max 16.9), delayTime median 15491 ms, warm 449 ms, failures |
| 20261008T0402Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fboff_fetched: cold median 114.7 s (min 114.7, max 114.7), delayTime median 111921 ms, warm 1956 ms, fai |
| 20261008T0402Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fbon_fetched: cold median 157.7 s (min 157.7, max 157.7), delayTime median 154694 ms, warm 953 ms, failu |
| 20261008T0402Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median 29.7 s (min 29.7, max 29.7), delayTime median 28193 ms, warm 1452 ms, failur |
| 20261008T0402Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fbon_fetched: cold median 145.5 s (min 145.5, max 145.5), delayTime median 142866 ms, warm 4926 ms, fai |
| 20261008T0402Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fboff_fetched: cold median 23.7 s (min 23.7, max 23.7), delayTime median 21426 ms, warm 1344 ms, failur |
| 20261008T0402Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fbon_fetched: cold median 24.7 s (min 24.7, max 24.7), delayTime median 22174 ms, warm 2073 ms, failure |
| 20261008T0402Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 143.5 s (min 143.5, max 143.5), delayTime median 141758 ms, warm 512 ms, failu |
| 20261008T0402Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fbon_wvllm: cold median 148.1 s (min 148.1, max 148.1), delayTime median 145728 ms, warm 571 ms, failur |
| 20261008T0402Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fboff_wvllm: cold median 148.3 s (min 148.3, max 148.3), delayTime median 146673 ms, warm 1184 ms, failu |
| 20261008T0402Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fbon_wvllm: cold median 147.4 s (min 147.4, max 147.4), delayTime median 144962 ms, warm 2059 ms, failur |
| 20261008T0402Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fboff_wvllm: cold median 888.9 s (min 888.9, max 888.9), delayTime median 887419 ms, warm 1347 ms, fail |
| 20261008T0402Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median - s (min -, max -), delayTime median None ms, warm 401612 ms, failures 1, not c |
| 20261008T0402Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 133.9 s (min 133.9, max 133.9), delayTime median 132287 ms, warm 811 ms, failu |
| 20261008T0402Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 206.5 s (min 206.5, max 206.5), delayTime median 203829 ms, warm 869 ms, failur |
| 20261008T0311Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T0311Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | backfilled: slot killed before it wrote runs.csv (409 race + crash loop) |
| 20261008T1414Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 135.2 s (min 135.2, max 135.2), delayTime median 132732 ms, warm 1003 ms, fa |
| 20261008T1414Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 169.3 s (min 169.3, max 169.3), delayTime median 168486 ms, warm 950 ms, failu |
| 20261008T1414Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 171.4 s (min 171.4, max 171.4), delayTime median 168797 ms, warm 1269 ms, fail |
| 20261008T1414Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median 37.6 s (min 37.6, max 37.6), delayTime median 33574 ms, warm 1104 ms, failure |
| 20261008T1414Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fboff_fetched: cold median 115.4 s (min 115.4, max 115.4), delayTime median 113288 ms, warm 1475 ms, fai |
| 20261008T1414Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fbon_wvllm: cold median 174.2 s (min 174.2, max 174.2), delayTime median 171483 ms, warm 1310 ms, failu |
| 20261008T1414Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 558.2 s (min 558.2, max 558.2), delayTime median 555860 ms, warm 1082 ms, failu |
| 20261008T1414Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fbon_fetched: cold median 42.5 s (min 42.5, max 42.5), delayTime median 38620 ms, warm 1131 ms, failures |
| 20261008T1414Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fboff_wvllm: cold median 184.1 s (min 184.1, max 184.1), delayTime median 181787 ms, warm 757 ms, failur |
| 20261008T1414Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 469.0 s (min 469.0, max 469.0), delayTime median 465841 ms, warm 714 ms, failur |
| 20261008T1414Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median 771.3 s (min 771.3, max 771.3), delayTime median 768223 ms, warm 452 ms, fai |
| 20261008T1414Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 20.8 s (min 20.8, max 20.8), delayTime median 18466 ms, warm 1589 ms, failures 0 |
| 20261008T1414Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fbon_wvllm: cold median 177.2 s (min 177.2, max 177.2), delayTime median 174825 ms, warm 1274 ms, failur |
| 20261008T1414Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fboff_wvllm: cold median 1103.5 s (min 1103.5, max 1103.5), delayTime median 1100874 ms, warm 1033 ms,  |

## Acknowledged overruns (campaign/spend_ack.csv)

| date (UTC) | endpoint | $ | reason |
|---|---|---|---|
| 2026-10-08 | h90byyjfb0ofbu | 0.70 | crash loop 03:11-04:01 UTC: the baked image (needs CUDA >= 12.8) was placed on a 4090 host with an older driver; the container failed to start every ~20 s for 50 min and the worker was billed the whole time. Fixed by setting minCudaVersion per image (campaign/grid.json min_cuda_version); reviewed by the owner 2026-10-08. |

## Approved estimate (campaign/estimate.csv)

| cell | est $ (total) |
|---|---|
| 4090_fboff_baked | 0.14 |
| 4090_fbon_baked | 0.14 |
| a40_fboff_baked | 0.15 |
| a40_fbon_baked | 0.15 |
| a100_fboff_baked | 0.34 |
| a100_fbon_baked | 0.34 |
| h100_fboff_baked | 0.6 |
| h100_fbon_baked | 0.6 |
| 4090_fboff_fetched | 0.25 |
| 4090_fbon_fetched | 0.25 |
| a40_fboff_fetched | 0.28 |
| a40_fbon_fetched | 0.28 |
| a100_fboff_fetched | 0.62 |
| a100_fbon_fetched | 0.62 |
| h100_fboff_fetched | 1.1 |
| h100_fbon_fetched | 1.1 |
| 4090_fboff_wvllm | 0.87 |
| 4090_fbon_wvllm | 0.87 |
| a40_fboff_wvllm | 0.97 |
| a40_fbon_wvllm | 0.97 |
| a100_fboff_wvllm | 2.15 |
| a100_fbon_wvllm | 2.15 |
| h100_fboff_wvllm | 3.79 |
| h100_fbon_wvllm | 3.79 |

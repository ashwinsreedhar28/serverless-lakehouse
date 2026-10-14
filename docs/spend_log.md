# Spend log

Actual $ from Runpod's `GET /v2/billing/serverless` (hourly buckets, via the poller; polls 2026-10-07 22:28:14 → 2026-10-14 16:44:17 UTC). Estimates from `campaign/runs.csv` and 0.013 $/run for the load generator. Rule: stop when an endpoint's actual exceeds its estimate by 20%. Generated 2026-10-14 16:45 UTC.

## Per endpoint

| endpoint | name | estimated $ | actual $ | acknowledged $ | ratio (actual − ack) / est | status |
|---|---|---|---|---|---|---|
| 74ulbugzbbba8o |  | 0.0000 | 0.1069 | 0.0000 | — | — |
| h90byyjfb0ofbu | pagedserve0929z | 1.8337 | 2.2660 | 0.7000 | 0.85 | ok |
| nfr1cqjnqikgwm | pagedserve | 0.0000 | 2.2651 | 0.0000 | — | — |
| ri6eo614hmu510 | pagedserve0929x | 3.1464 | 2.7319 | 0.0000 | 0.87 | ok |
| rvy2p7bfia91fm | pagedserve0929 | 12.0287 | 11.5927 | 0.0000 | 0.96 | ok |

**Total actual: $18.9626** · total estimated: $17.0088

## Per endpoint per day (actual)

| day (UTC) | endpoint | name | total $ | gpu $ | billed hours |
|---|---|---|---|---|---|
| 2026-10-06 | 74ulbugzbbba8o |  | 0.1069 | 0.1067 | 2 |
| 2026-10-08 | h90byyjfb0ofbu | pagedserve0929z | 0.9994 | 0.9989 | 7 |
| 2026-10-08 | nfr1cqjnqikgwm | pagedserve | 0.0476 | 0.0476 | 2 |
| 2026-10-08 | ri6eo614hmu510 | pagedserve0929x | 0.7531 | 0.7517 | 4 |
| 2026-10-08 | rvy2p7bfia91fm | pagedserve0929 | 2.2674 | 2.2448 | 8 |
| 2026-10-09 | h90byyjfb0ofbu | pagedserve0929z | 0.5641 | 0.5640 | 9 |
| 2026-10-09 | nfr1cqjnqikgwm | pagedserve | 0.2919 | 0.2918 | 11 |
| 2026-10-09 | ri6eo614hmu510 | pagedserve0929x | 0.9472 | 0.9449 | 10 |
| 2026-10-09 | rvy2p7bfia91fm | pagedserve0929 | 4.0218 | 3.9906 | 11 |
| 2026-10-10 | h90byyjfb0ofbu | pagedserve0929z | 0.5767 | 0.5767 | 8 |
| 2026-10-10 | nfr1cqjnqikgwm | pagedserve | 0.3450 | 0.3449 | 22 |
| 2026-10-10 | ri6eo614hmu510 | pagedserve0929x | 1.0171 | 1.0152 | 7 |
| 2026-10-10 | rvy2p7bfia91fm | pagedserve0929 | 3.9738 | 3.9426 | 8 |
| 2026-10-11 | h90byyjfb0ofbu | pagedserve0929z | 0.1258 | 0.1258 | 4 |
| 2026-10-11 | nfr1cqjnqikgwm | pagedserve | 0.4101 | 0.4101 | 24 |
| 2026-10-11 | ri6eo614hmu510 | pagedserve0929x | 0.0145 | 0.0145 | 1 |
| 2026-10-11 | rvy2p7bfia91fm | pagedserve0929 | 1.3297 | 1.3210 | 7 |
| 2026-10-12 | nfr1cqjnqikgwm | pagedserve | 0.3962 | 0.3959 | 23 |
| 2026-10-13 | nfr1cqjnqikgwm | pagedserve | 0.4111 | 0.4110 | 24 |
| 2026-10-14 | nfr1cqjnqikgwm | pagedserve | 0.3632 | 0.3631 | 16 |

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
| 20261008T1710Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 155.7 s (min 155.7, max 155.7), delayTime median 150770 ms, warm 1033 ms, fa |
| 20261008T1710Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 242.5 s (min 242.5, max 242.5), delayTime median 240247 ms, warm 588 ms, failu |
| 20261008T1710Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fbon_wvllm: cold median 242.3 s (min 242.3, max 242.3), delayTime median 240304 ms, warm 555 ms, failur |
| 20261008T1710Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median 172.5 s (min 172.5, max 172.5), delayTime median 169939 ms, warm 1199 ms, fai |
| 20261008T1710Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fboff_fetched: cold median 25.2 s (min 25.2, max 25.2), delayTime median 23334 ms, warm 817 ms, failures |
| 20261008T1710Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 924.5 s (min 924.5, max 924.5), delayTime median 921045 ms, warm 1166 ms, fail |
| 20261008T1710Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fboff_wvllm: cold median 151.3 s (min 151.3, max 151.3), delayTime median 149193 ms, warm 782 ms, failur |
| 20261008T1710Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fbon_fetched: cold median 31.2 s (min 31.2, max 31.2), delayTime median 28987 ms, warm 919 ms, failures  |
| 20261008T1710Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fbon_wvllm: cold median 258.5 s (min 258.5, max 258.5), delayTime median 256087 ms, warm 786 ms, failure |
| 20261008T1710Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 19.2 s (min 19.2, max 19.2), delayTime median 17586 ms, warm 551 ms, failures 0 |
| 20261008T1710Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median 343.6 s (min 343.6, max 343.6), delayTime median 340023 ms, warm 720 ms, fai |
| 20261008T1710Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 174.8 s (min 174.8, max 174.8), delayTime median 171677 ms, warm 869 ms, failur |
| 20261008T1710Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fbon_fetched: cold median 190.3 s (min 190.3, max 190.3), delayTime median 188206 ms, warm 400 ms, fail |
| 20261008T1710Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 19.4 s (min 19.4, max 19.4), delayTime median 17490 ms, warm 716 ms, failures 0, |
| 20261008T1710Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fboff_wvllm: cold median 791.7 s (min 791.7, max 791.7), delayTime median 788699 ms, warm 969 ms, failu |
| 20261008T1710Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fboff_fetched: cold median 62.6 s (min 62.6, max 62.6), delayTime median 60441 ms, warm 1044 ms, failur |
| 20261008T1710Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fbon_fetched: cold median 187.6 s (min 187.6, max 187.6), delayTime median 183271 ms, warm 1260 ms, fai |
| 20261008T1710Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 555.7 s (min 555.7, max 555.7), delayTime median 554147 ms, warm 559 ms, failu |
| 20261008T1710Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 132.5 s (min 132.5, max 132.5), delayTime median 129586 ms, warm 536 ms, failur |
| 20261008T1710Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 358.7 s (min 358.7, max 358.7), delayTime median 567220 ms, warm 1609 ms, fail |
| 20261008T1710Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=1 httpx.RemoteProtocolError: Server disconnected without sending a response. |
| 20261008T1710Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 88.9 s (min 88.9, max 88.9), delayTime median 151061 ms, warm 910 ms, failures |
| 20261008T1710Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=1 httpx.ReadTimeout: The read operation timed out |
| 20261008T1710Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=1 httpx.RemoteProtocolError: Server disconnected without sending a response. |
| 20261008T2321Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=1 httpx.ReadTimeout: The read operation timed out |
| 20261008T2321Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=1 httpx.ReadTimeout: The read operation timed out |
| 20261008T2321Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=1 httpx.ReadTimeout: The read operation timed out |
| 20261008T2321Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median - s (min -, max -), delayTime median None ms, warm None ms, failures 1, not c |
| 20261008T2321Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 145.0 s (min 145.0, max 145.0), delayTime median 141023 ms, warm 773 ms, failur |
| 20261008T2321Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fbon_wvllm: cold median 158.0 s (min 158.0, max 158.0), delayTime median 156303 ms, warm 1119 ms, failu |
| 20261008T2321Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fboff_fetched: cold median 19.8 s (min 19.8, max 19.8), delayTime median 18050 ms, warm 750 ms, failures |
| 20261008T2321Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 269.6 s (min 269.6, max 269.6), delayTime median 267269 ms, warm 1141 ms, failu |
| 20261008T2321Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fboff_wvllm: cold median 153.7 s (min 153.7, max 153.7), delayTime median 150890 ms, warm 1204 ms, failu |
| 20261008T2321Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fbon_fetched: cold median 31.0 s (min 31.0, max 31.0), delayTime median 28360 ms, warm 652 ms, failures  |
| 20261008T2321Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 19.6 s (min 19.6, max 19.6), delayTime median 16849 ms, warm 1432 ms, failures 0 |
| 20261008T2321Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fbon_wvllm: cold median 144.4 s (min 144.4, max 144.4), delayTime median 142478 ms, warm 1163 ms, failur |
| 20261008T2321Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 131.6 s (min 131.6, max 131.6), delayTime median 128488 ms, warm 431 ms, failu |
| 20261008T2321Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median 168.8 s (min 168.8, max 168.8), delayTime median 166273 ms, warm 1043 ms, fa |
| 20261008T2321Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 18.7 s (min 18.7, max 18.7), delayTime median 15501 ms, warm 432 ms, failures 0 |
| 20261008T2321Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fbon_fetched: cold median 34.6 s (min 34.6, max 34.6), delayTime median 32736 ms, warm 406 ms, failures |
| 20261008T2321Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 12.8 s (min 12.8, max 12.8), delayTime median 11263 ms, warm 1103 ms, failures |
| 20261008T2321Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fboff_fetched: cold median 157.6 s (min 157.6, max 157.6), delayTime median 154544 ms, warm 1004 ms, fa |
| 20261008T2321Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fboff_wvllm: cold median 1096.1 s (min 1096.1, max 1096.1), delayTime median 1094594 ms, warm 2522 ms,  |
| 20261008T2321Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 13.5 s (min 13.5, max 13.5), delayTime median 12008 ms, warm 712 ms, failures 0 |
| 20261008T2321Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fbon_fetched: cold median 26.7 s (min 26.7, max 26.7), delayTime median 24027 ms, warm 2016 ms, failure |
| 20261008T2321Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 1280.3 s (min 1280.3, max 1280.3), delayTime median 1278424 ms, warm 1053 ms, f |
| 20261008T2321Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 1122.3 s (min 1122.3, max 1122.3), delayTime median 1120500 ms, warm 454 ms, f |
| 20261008T2321Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median - s (min -, max -), delayTime median None ms, warm 286912 ms, failures 1, not c |
| 20261009T0510Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 18.3 s (min 18.3, max 18.3), delayTime median 15269 ms, warm 1046 ms, failur |
| 20261009T0510Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 132.2 s (min 132.2, max 132.2), delayTime median 128897 ms, warm 658 ms, failu |
| 20261009T0510Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 138.4 s (min 138.4, max 138.4), delayTime median 136558 ms, warm 550 ms, failu |
| 20261009T0510Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median 20.3 s (min 20.3, max 20.3), delayTime median 18585 ms, warm 501 ms, failures |
| 20261009T0510Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 18.2 s (min 18.2, max 18.2), delayTime median 16681 ms, warm 465 ms, failures 0 |
| 20261009T0510Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fbon_wvllm: cold median 133.5 s (min 133.5, max 133.5), delayTime median 132474 ms, warm 1702 ms, failu |
| 20261009T0510Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fboff_fetched: cold median 33.3 s (min 33.3, max 33.3), delayTime median 30987 ms, warm 1227 ms, failure |
| 20261009T0510Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fbon_fetched: cold median 19.2 s (min 19.2, max 19.2), delayTime median 17026 ms, warm 1193 ms, failures |
| 20261009T0510Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 15.1 s (min 15.1, max 15.1), delayTime median 13269 ms, warm 715 ms, failures 0 |
| 20261009T0510Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median 190.1 s (min 190.1, max 190.1), delayTime median 187792 ms, warm 1001 ms, fa |
| 20261009T0510Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fboff_wvllm: cold median 172.8 s (min 172.8, max 172.8), delayTime median 171115 ms, warm 1249 ms, failu |
| 20261009T0510Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 13.3 s (min 13.3, max 13.3), delayTime median 10834 ms, warm 1173 ms, failures 0 |
| 20261009T0510Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fbon_fetched: cold median 32.1 s (min 32.1, max 32.1), delayTime median 30477 ms, warm 462 ms, failures |
| 20261009T0510Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 314.4 s (min 314.4, max 314.4), delayTime median 311942 ms, warm 468 ms, failu |
| 20261009T0510Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fbon_wvllm: cold median 149.1 s (min 149.1, max 149.1), delayTime median 146232 ms, warm 1297 ms, failur |
| 20261009T0510Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fboff_fetched: cold median 62.7 s (min 62.7, max 62.7), delayTime median 61407 ms, warm 338 ms, failure |
| 20261009T0510Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 17.9 s (min 17.9, max 17.9), delayTime median 16230 ms, warm 518 ms, failures 0 |
| 20261009T0510Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fboff_wvllm: cold median 310.6 s (min 310.6, max 310.6), delayTime median 309253 ms, warm 1063 ms, fail |
| 20261009T0510Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fbon_fetched: cold median 26.6 s (min 26.6, max 26.6), delayTime median 24420 ms, warm 1298 ms, failure |
| 20261009T0510Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 463.9 s (min 463.9, max 463.9), delayTime median 462470 ms, warm 420 ms, failu |
| 20261009T0510Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 759.6 s (min 759.6, max 759.6), delayTime median 757959 ms, warm 979 ms, failur |
| 20261009T0510Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 159.7 s (min 159.7, max 159.7), delayTime median 158523 ms, warm 1136 ms, fail |
| 20261009T0510Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 345.4 s (min 345.4, max 345.4), delayTime median 341545 ms, warm 1354 ms, failu |
| 20261009T0510Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 261.3 s (min 261.3, max 261.3), delayTime median 259538 ms, warm 454 ms, failur |
| 20261009T1110Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=1 httpx.ReadTimeout: The read operation timed out |
| 20261009T1110Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=1 httpx.ReadTimeout: The read operation timed out |
| 20261009T1110Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=1 httpx.ReadTimeout: The read operation timed out |
| 20261009T1110Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median - s (min -, max -), delayTime median None ms, warm 42650 ms, failures 1, not  |
| 20261009T1110Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fbon_wvllm: cold median 147.7 s (min 147.7, max 147.7), delayTime median 145294 ms, warm 2185 ms, failu |
| 20261009T1110Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 231.2 s (min 231.2, max 231.2), delayTime median 228509 ms, warm 2210 ms, failu |
| 20261009T1110Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fboff_wvllm: cold median 170.9 s (min 170.9, max 170.9), delayTime median 169396 ms, warm 2202 ms, failu |
| 20261009T1110Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fboff_fetched: cold median 41.1 s (min 41.1, max 41.1), delayTime median 38383 ms, warm 2176 ms, failure |
| 20261009T1110Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fbon_wvllm: cold median 174.3 s (min 174.3, max 174.3), delayTime median 172522 ms, warm 2150 ms, failur |
| 20261009T1110Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fbon_fetched: cold median 80.0 s (min 80.0, max 80.0), delayTime median 77621 ms, warm 2221 ms, failures |
| 20261009T1110Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 316.1 s (min 316.1, max 316.1), delayTime median 313474 ms, warm 2629 ms, failu |
| 20261009T1110Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 19.2 s (min 19.2, max 19.2), delayTime median 16577 ms, warm 2245 ms, failures 0 |
| 20261009T1110Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fboff_wvllm: cold median 644.8 s (min 644.8, max 644.8), delayTime median 642709 ms, warm 2220 ms, fail |
| 20261009T1110Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 234.3 s (min 234.3, max 234.3), delayTime median 230963 ms, warm 2220 ms, fail |
| 20261009T1110Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 2185.4 s (min 2185.4, max 2185.4), delayTime median 2183052 ms, warm 2177 ms, f |
| 20261009T1110Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 112.4 s (min 112.4, max 112.4), delayTime median 110154 ms, warm 2221 ms, fail |
| 20261009T1110Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median - s (min -, max -), delayTime median None ms, warm 146525 ms, failures 1, not c |
| 20261009T1110Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median - s (min -, max -), delayTime median None ms, warm None ms, failures 1, not  |
| 20261009T1110Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 214.4 s (min 214.4, max 214.4), delayTime median 211861 ms, warm 2202 ms, fail |
| 20261009T1110Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 178.3 s (min 178.3, max 178.3), delayTime median 175677 ms, warm 2200 ms, failu |
| 20261009T1110Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 178.3 s (min 178.3, max 178.3), delayTime median 176571 ms, warm 2201 ms, failu |
| 20261009T1110Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fbon_fetched: cold median 1024.4 s (min 1024.4, max 1024.4), delayTime median 1021439 ms, warm 2212 ms, |
| 20261009T1110Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fboff_fetched: cold median 89.2 s (min 89.2, max 89.2), delayTime median 86462 ms, warm 2230 ms, failur |
| 20261009T1110Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fbon_fetched: cold median 29.9 s (min 29.9, max 29.9), delayTime median 25606 ms, warm 2187 ms, failure |
| 20261009T1710Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 181.1 s (min 181.1, max 181.1), delayTime median 179799 ms, warm 2289 ms, fail |
| 20261009T1710Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 35.5 s (min 35.5, max 35.5), delayTime median 31910 ms, warm 2663 ms, failur |
| 20261009T1710Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 75.0 s (min 75.0, max 75.0), delayTime median 71548 ms, warm 2697 ms, failures |
| 20261009T1710Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fbon_wvllm: cold median 149.5 s (min 149.5, max 149.5), delayTime median 148119 ms, warm 2356 ms, failu |
| 20261009T1710Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median 21.3 s (min 21.3, max 21.3), delayTime median 18834 ms, warm 2187 ms, failure |
| 20261009T1710Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 21.4 s (min 21.4, max 21.4), delayTime median 18872 ms, warm 2179 ms, failures  |
| 20261009T1710Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fboff_wvllm: cold median 159.7 s (min 159.7, max 159.7), delayTime median 157309 ms, warm 2199 ms, failu |
| 20261009T1710Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fbon_wvllm: cold median 157.3 s (min 157.3, max 157.3), delayTime median 154416 ms, warm 2273 ms, failur |
| 20261009T1710Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fboff_fetched: cold median 44.2 s (min 44.2, max 44.2), delayTime median 41032 ms, warm 2255 ms, failure |
| 20261009T1710Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median - s (min -, max -), delayTime median None ms, warm 15830 ms, failures 1, not co |
| 20261009T1710Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fbon_fetched: cold median 42.6 s (min 42.6, max 42.6), delayTime median 39415 ms, warm 2174 ms, failures |
| 20261009T1710Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 15.1 s (min 15.1, max 15.1), delayTime median 12665 ms, warm 2186 ms, failures 0 |
| 20261009T1710Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fboff_wvllm: cold median 734.1 s (min 734.1, max 734.1), delayTime median 731977 ms, warm 2288 ms, fail |
| 20261009T1710Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 693.2 s (min 693.2, max 693.2), delayTime median 691076 ms, warm 2505 ms, failu |
| 20261009T1710Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 928.2 s (min 928.2, max 928.2), delayTime median 924007 ms, warm 2195 ms, fail |
| 20261009T1710Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 154.4 s (min 154.4, max 154.4), delayTime median 151790 ms, warm 2258 ms, fail |
| 20261009T1710Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 35.4 s (min 35.4, max 35.4), delayTime median 30966 ms, warm 2271 ms, failures  |
| 20261009T1710Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 213.6 s (min 213.6, max 213.6), delayTime median 213128 ms, warm 2293 ms, failu |
| 20261009T1710Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 13.4 s (min 13.4, max 13.4), delayTime median 11709 ms, warm 2292 ms, failures |
| 20261009T1710Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median 2235.2 s (min 2235.2, max 2235.2), delayTime median 2233349 ms, warm 2300 ms |
| 20261009T1710Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 301.8 s (min 301.8, max 301.8), delayTime median 299277 ms, warm 2278 ms, failu |
| 20261009T1710Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fbon_fetched: cold median 2130.8 s (min 2130.8, max 2130.8), delayTime median 2126988 ms, warm 2263 ms, |
| 20261009T1710Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fboff_fetched: cold median 66.8 s (min 66.8, max 66.8), delayTime median 62368 ms, warm 2179 ms, failur |
| 20261009T1710Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fbon_fetched: cold median 24.3 s (min 24.3, max 24.3), delayTime median 21286 ms, warm 2277 ms, failure |
| 20261009T2310Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 127.1 s (min 127.1, max 127.1), delayTime median 125672 ms, warm 2212 ms, fail |
| 20261009T2310Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 144.1 s (min 144.1, max 144.1), delayTime median 140712 ms, warm 2184 ms, fail |
| 20261009T2310Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 131.5 s (min 131.5, max 131.5), delayTime median 129374 ms, warm 2197 ms, failu |
| 20261009T2310Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 27.7 s (min 27.7, max 27.7), delayTime median 25307 ms, warm 2204 ms, failur |
| 20261009T2310Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median 87.5 s (min 87.5, max 87.5), delayTime median 84015 ms, warm 2251 ms, failure |
| 20261009T2310Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fbon_wvllm: cold median 135.9 s (min 135.9, max 135.9), delayTime median 134445 ms, warm 2254 ms, failu |
| 20261009T2310Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 41.8 s (min 41.8, max 41.8), delayTime median 38378 ms, warm 2241 ms, failures  |
| 20261009T2310Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fboff_wvllm: cold median 166.1 s (min 166.1, max 166.1), delayTime median 163893 ms, warm 2272 ms, failu |
| 20261009T2310Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fboff_fetched: cold median 24.2 s (min 24.2, max 24.2), delayTime median 22015 ms, warm 2245 ms, failure |
| 20261009T2310Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fbon_fetched: cold median 20.0 s (min 20.0, max 20.0), delayTime median 16073 ms, warm 2252 ms, failures |
| 20261009T2310Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median 26.4 s (min 26.4, max 26.4), delayTime median 23008 ms, warm 2269 ms, failur |
| 20261009T2310Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 92.1 s (min 92.1, max 92.1), delayTime median 90178 ms, warm 2275 ms, failures 0 |
| 20261009T2310Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fbon_wvllm: cold median 65.7 s (min 65.7, max 65.7), delayTime median 144674 ms, warm 2267 ms, failures  |
| 20261009T2310Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fbon_fetched: cold median 18.1 s (min 18.1, max 18.1), delayTime median 155206 ms, warm 2274 ms, failur |
| 20261009T2310Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 22.7 s (min 22.7, max 22.7), delayTime median 236994 ms, warm 35330 ms, failur |
| 20261009T2310Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fboff_wvllm: cold median 43.7 s (min 43.7, max 43.7), delayTime median 252107 ms, warm 2449 ms, failure |
| 20261009T2310Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 21.2 s (min 21.2, max 21.2), delayTime median 18764 ms, warm 2182 ms, failures  |
| 20261009T2310Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fboff_fetched: cold median 61.5 s (min 61.5, max 61.5), delayTime median 58826 ms, warm 2190 ms, failur |
| 20261009T2310Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 232.5 s (min 232.5, max 232.5), delayTime median 230782 ms, warm 2193 ms, fail |
| 20261009T2310Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 585.5 s (min 585.5, max 585.5), delayTime median 583118 ms, warm 2210 ms, failu |
| 20261009T2310Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fbon_fetched: cold median 74.4 s (min 74.4, max 74.4), delayTime median 71740 ms, warm 2183 ms, failure |
| 20261009T2310Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 159.0 s (min 159.0, max 159.0), delayTime median 157334 ms, warm 2232 ms, fail |
| 20261009T2310Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 17.9 s (min 17.9, max 17.9), delayTime median 15273 ms, warm 2250 ms, failures  |
| 20261009T2310Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 156.3 s (min 156.3, max 156.3), delayTime median 154541 ms, warm 2271 ms, failu |
| 20261010T0510Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 33.9 s (min 33.9, max 33.9), delayTime median 31155 ms, warm 2161 ms, failur |
| 20261010T0510Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 143.6 s (min 143.6, max 143.6), delayTime median 140190 ms, warm 2190 ms, fail |
| 20261010T0510Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 147.8 s (min 147.8, max 147.8), delayTime median 146763 ms, warm 2194 ms, fail |
| 20261010T0510Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median 99.6 s (min 99.6, max 99.6), delayTime median 97460 ms, warm 2190 ms, failure |
| 20261010T0510Z | 4090_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fbon_wvllm: cold median 154.3 s (min 154.3, max 154.3), delayTime median 151799 ms, warm 2198 ms, failu |
| 20261010T0510Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 182.0 s (min 182.0, max 182.0), delayTime median 179730 ms, warm 2183 ms, failu |
| 20261010T0510Z | a40_fboff_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fboff_fetched: cold median 24.1 s (min 24.1, max 24.1), delayTime median 21736 ms, warm 2215 ms, failure |
| 20261010T0510Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 428.7 s (min 428.7, max 428.7), delayTime median 425968 ms, warm 2252 ms, failu |
| 20261010T0510Z | a40_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fboff_wvllm: cold median 157.5 s (min 157.5, max 157.5), delayTime median 154523 ms, warm 2279 ms, failu |
| 20261010T0510Z | a40_fbon_fetched | ri6eo614hmu510 | 1 | 0.0186 | rc=0 [coldstart] a40_fbon_fetched: cold median 24.2 s (min 24.2, max 24.2), delayTime median 20061 ms, warm 2225 ms, failures |
| 20261010T0510Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median 28.5 s (min 28.5, max 28.5), delayTime median 25823 ms, warm 2263 ms, failur |
| 20261010T0510Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 407.5 s (min 407.5, max 407.5), delayTime median 405211 ms, warm 2252 ms, failur |
| 20261010T0510Z | a40_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.0644 | rc=0 [coldstart] a40_fbon_wvllm: cold median 148.6 s (min 148.6, max 148.6), delayTime median 147199 ms, warm 2270 ms, failur |
| 20261010T0510Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fbon_fetched: cold median 22.1 s (min 22.1, max 22.1), delayTime median 19718 ms, warm 2198 ms, failure |
| 20261010T0510Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fboff_fetched: cold median 109.6 s (min 109.6, max 109.6), delayTime median 107160 ms, warm 2305 ms, fa |
| 20261010T0510Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fbon_fetched: cold median 61.4 s (min 61.4, max 61.4), delayTime median 59966 ms, warm 2246 ms, failure |
| 20261010T0510Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 730.6 s (min 730.6, max 730.6), delayTime median 728127 ms, warm 2260 ms, fail |
| 20261010T0510Z | a100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fboff_wvllm: cold median 737.5 s (min 737.5, max 737.5), delayTime median 735483 ms, warm 2263 ms, fail |
| 20261010T0510Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 50.4 s (min 50.4, max 50.4), delayTime median 47366 ms, warm 2256 ms, failures  |
| 20261010T0510Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 17.7 s (min 17.7, max 17.7), delayTime median 16104 ms, warm 2260 ms, failures |
| 20261010T0510Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 13.2 s (min 13.2, max 13.2), delayTime median 10889 ms, warm 2267 ms, failures  |
| 20261010T0510Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median - s (min -, max -), delayTime median None ms, warm 39413 ms, failures 1, not co |
| 20261010T0510Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 135.8 s (min 135.8, max 135.8), delayTime median 133210 ms, warm 2253 ms, fail |
| 20261010T0510Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 140.4 s (min 140.4, max 140.4), delayTime median 138562 ms, warm 2271 ms, failu |
| 20261010T1110Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 35.1 s (min 35.1, max 35.1), delayTime median 32393 ms, warm 2243 ms, failur |
| 20261010T1110Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 129.0 s (min 129.0, max 129.0), delayTime median 126319 ms, warm 2263 ms, fail |
| 20261010T1110Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median 43.9 s (min 43.9, max 43.9), delayTime median 41887 ms, warm 2269 ms, failure |
| 20261010T1110Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 148.8 s (min 148.8, max 148.8), delayTime median 147789 ms, warm 2261 ms, fail |
| 20261010T1110Z | 4090_fbon_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fbon_baked: cold median 22.1 s (min 22.1, max 22.1), delayTime median 18677 ms, warm 2217 ms, failures  |
| 20261010T1110Z | a100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fboff_fetched: cold median 254.2 s (min 254.2, max 254.2), delayTime median 248517 ms, warm 2270 ms, fa |
| 20261010T1110Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 902.3 s (min 902.3, max 902.3), delayTime median 900017 ms, warm 2265 ms, failu |
| 20261010T1110Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 357.1 s (min 357.1, max 357.1), delayTime median 353379 ms, warm 2280 ms, failu |
| 20261010T1110Z | a100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0416 | rc=0 [coldstart] a100_fbon_fetched: cold median 567.9 s (min 567.9, max 567.9), delayTime median 563047 ms, warm 2288 ms, fai |
| 20261010T1110Z | a40_fbon_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fbon_baked: cold median 17.6 s (min 17.6, max 17.6), delayTime median 15351 ms, warm 2237 ms, failures 0 |
| 20261010T1110Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 169.1 s (min 169.1, max 169.1), delayTime median 166551 ms, warm 2296 ms, fail |
| 20261010T1110Z | h100_fboff_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fboff_fetched: cold median 44.4 s (min 44.4, max 44.4), delayTime median 983394 ms, warm 2261 ms, failu |
| 20261010T1110Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 68.1 s (min 68.1, max 68.1), delayTime median 1047104 ms, warm 6811 ms, failur |
| 20261010T1110Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 31.4 s (min 31.4, max 31.4), delayTime median 166450 ms, warm 52017 ms, failure |
| 20261010T1110Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median - s (min -, max -), delayTime median None ms, warm 55314 ms, failures 1, not co |
| 20261010T1110Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 141.1 s (min 141.1, max 141.1), delayTime median 1096029 ms, warm 8829 ms, fai |
| 20261010T1110Z | h100_fbon_fetched | ri6eo614hmu510 | 1 | 0.0732 | rc=0 [coldstart] h100_fbon_fetched: cold median 11.9 s (min 11.9, max 11.9), delayTime median 29458 ms, warm 6667 ms, failure |
| 20261010T1110Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median - s (min -, max -), delayTime median None ms, warm 7224 ms, failures 1, not col |
| 20261010T1715Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 13.5 s (min 13.5, max 13.5), delayTime median 174437 ms, warm 2270 ms, failure |
| 20261010T1715Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 24.8 s (min 24.8, max 24.8), delayTime median 149734 ms, warm 21860 ms, fail |
| 20261010T1715Z | 4090_fboff_baked | h90byyjfb0ofbu | 1 | 0.0092 | rc=0 [coldstart] 4090_fboff_baked: cold median 57.6 s (min 57.6, max 57.6), delayTime median 277911 ms, warm 2487 ms, failure |
| 20261010T1715Z | 4090_fbon_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fbon_fetched: cold median 13.2 s (min 13.2, max 13.2), delayTime median 22457 ms, warm 2263 ms, failure |
| 20261010T1715Z | a40_fboff_baked | h90byyjfb0ofbu | 1 | 0.0102 | rc=0 [coldstart] a40_fboff_baked: cold median 38.2 s (min 38.2, max 38.2), delayTime median 930562 ms, warm 14938 ms, failure |
| 20261010T1715Z | a100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fboff_baked: cold median 19.2 s (min 19.2, max 19.2), delayTime median 17176 ms, warm 2168 ms, failures |
| 20261010T1715Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 73.7 s (min 73.7, max 73.7), delayTime median 742356 ms, warm 624580 ms, failur |
| 20261010T1715Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 19.5 s (min 19.5, max 19.5), delayTime median 15733 ms, warm 2180 ms, failures  |
| 20261010T1715Z | h100_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fboff_wvllm: cold median 171.1 s (min 171.1, max 171.1), delayTime median 170181 ms, warm 2210 ms, fail |
| 20261010T1715Z | h100_fboff_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fboff_baked: cold median 65.8 s (min 65.8, max 65.8), delayTime median 62349 ms, warm 2162 ms, failures |
| 20261010T1715Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 17.0 s (min 17.0, max 17.0), delayTime median 13537 ms, warm 2174 ms, failures  |
| 20261010T1715Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 163.3 s (min 163.3, max 163.3), delayTime median 161682 ms, warm 2182 ms, failu |
| 20261010T2316Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 72.0 s (min 72.0, max 72.0), delayTime median 69018 ms, warm 2178 ms, failur |
| 20261010T2316Z | 4090_fboff_wvllm | rvy2p7bfia91fm | 1 | 0.0581 | rc=0 [coldstart] 4090_fboff_wvllm: cold median 173.4 s (min 173.4, max 173.4), delayTime median 171838 ms, warm 2173 ms, fail |
| 20261010T2316Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median - s (min -, max -), delayTime median None ms, warm None ms, failures 1, not col |
| 20261010T2316Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median - s (min -, max -), delayTime median None ms, warm None ms, failures 1, not col |
| 20261010T2316Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median - s (min -, max -), delayTime median None ms, warm 2287 ms, failures 0, not col |
| 20261010T2316Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median - s (min -, max -), delayTime median None ms, warm 2265 ms, failures 0, not col |
| 20261011T0510Z | a100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0227 | rc=0 [coldstart] a100_fbon_baked: cold median 35.5 s (min 35.5, max 35.5), delayTime median 32609 ms, warm 2255 ms, failures  |
| 20261011T0510Z | 4090_fboff_fetched | ri6eo614hmu510 | 1 | 0.0168 | rc=0 [coldstart] 4090_fboff_fetched: cold median 44.4 s (min 44.4, max 44.4), delayTime median 42322 ms, warm 2251 ms, failur |
| 20261011T0510Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 191.7 s (min 191.7, max 191.7), delayTime median 188977 ms, warm 2268 ms, failu |
| 20261011T0510Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 15.8 s (min 15.8, max 15.8), delayTime median 12394 ms, warm 2376 ms, failures  |
| 20261011T0510Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 134.3 s (min 134.3, max 134.3), delayTime median 132558 ms, warm 2283 ms, failu |
| 20261011T1148Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 133.1 s (min 133.1, max 133.1), delayTime median 240051 ms, warm 2327 ms, failu |
| 20261011T1148Z | h100_fbon_baked | h90byyjfb0ofbu | 1 | 0.0399 | rc=0 [coldstart] h100_fbon_baked: cold median 46.4 s (min 46.4, max 46.4), delayTime median 117055 ms, warm 2271 ms, failures |
| 20261011T1148Z | h100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.2528 | rc=0 [coldstart] h100_fbon_wvllm: cold median 54.0 s (min 54.0, max 54.0), delayTime median 1197483 ms, warm 152188 ms, failu |
| 20261011T1710Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 436.2 s (min 436.2, max 436.2), delayTime median 434820 ms, warm 2326 ms, failu |
| 20261011T2310Z | a100_fbon_wvllm | rvy2p7bfia91fm | 1 | 0.1436 | rc=0 [coldstart] a100_fbon_wvllm: cold median 251.3 s (min 251.3, max 251.3), delayTime median 248956 ms, warm 2271 ms, failu |

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

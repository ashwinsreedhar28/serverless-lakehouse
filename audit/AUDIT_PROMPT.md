# Audit prompt — paste with `serverless-lakehouse-bundle.md` attached

You are reviewing a small data-engineering project before it goes public and gets read by a data team
(Staff Data Engineer and Head of Data at an inference-cloud company). Attached is the full repo as one file:
code, README, seeds, the gold report, a Streamlit app, and format samples of the raw inputs. The author will
be interviewed on it, so anything that is wrong, over-claimed, or would embarrass a careful reader matters more
than style.

Review it as three people in turn, then merge the findings.

1. **Data engineer.** Bronze/silver/gold boundaries, idempotency (bronze keys on (source_file, sha256)), lineage
   columns, schema handling (all-string CSV bronze, from_json in silver, Delta mergeSchema/overwriteSchema), the
   dedupe of two byte-identical CSVs, the three worker-log timestamp parsers (console GMT-0400, ISO Z, endpoint-logs
   laptop-local America/New_York), the boot-segmentation rule, and the `verify` step. Try to break idempotency:
   what happens on a re-landed file, a renamed file, a partially failed run, a file that changes type?
2. **Skeptical analyst.** Check every number in README.md "Headline numbers" and in docs/gold_report.md against
   the code that produces it and the seeds that feed it. Flag any claim the data cannot support, any metric whose
   name promises more than its definition (FlashBoot hit = cold-labelled request under 5,000 ms; cost =
   (delay+exec)/3.6e6 × $/hr, called an upper bound), any pooled figure quoted without its cohorts, and any
   seed row whose `source` does not justify the value.
3. **Security/ops reviewer.** Secrets handling (lakehouse/redact.py patterns, pre-commit hook, .env refusal),
   anything in the landing samples or seeds that should not be public (identifiers are accepted as non-secrets —
   challenge that if you disagree), the GitHub Action that uploads to a Hugging Face Space, pinned versions,
   and whether a fresh `git clone && make setup && make all` would actually work on macOS with Homebrew Java 17.

Output, in this order:
- **Blocking** findings (wrong result, leaked secret, false claim, broken reproduction) — each with file:line,
  what is wrong, how you know, and the smallest fix.
- **Should fix before sharing** — same format.
- **Interview exposure** — questions a data team would ask that the README does not pre-empt, with the answer
  the code actually supports.
- **What is good** — at most five bullets, specific, so the author knows what not to change.

Rules: cite file paths and line ranges from the bundle; do not rewrite files; do not invent data you cannot see
(the landing data is sampled, say so when a check needs the full file); when a claim depends on a seed value,
say which row. If you have code execution, clone https://github.com/ashwinsreedhar28/serverless-lakehouse and
run `make all FORMAT=parquet` (Java 11/17/21 needed) and `make test`; report the exact output.

# serverless-lakehouse — bronze/silver/gold over Runpod Serverless benchmark data.
#
#   make setup                     create .venv, install pinned PySpark + Delta, check Java
#   make land                      extract: copy + redact sources into data/landing/ (+ manifest)
#   make bronze [RUN_LABEL=...]    ingest data/landing/ into bronze Delta tables (append-only)
#   make verify                    bronze row counts vs. what the landing manifest says they should be
#   make silver                    bronze + seeds/ → typed, parsed, deduped silver tables (rebuilt in full)
#   make gold                      silver → the aggregate tables the dashboard reads (rebuilt in full)
#   make report                    render gold to docs/gold_report.md
#   make dashboard                 render gold to docs/dashboard.html (static) and space/data/gold.json (for the Space)
#   make space                     run the Streamlit dashboard locally (space/app.py) in its own venv
#   make space-login                `hf auth login` (browser code flow) — once per machine
#   make space-create HF_SPACE=u/n create the Space on huggingface.co (static SDK, free tier; idempotent), then upload docs/dashboard.html
#   make space-push HF_SPACE=u/n   re-upload the static dashboard to an existing Space (the GitHub Action does it on push)
#   make space-create-docker / space-push-docker   same for the Streamlit app in space/ (Docker SDK — needs an HF PRO plan)
#   make dataset-create [HF_DATASET=u/n]  publish data/landing (+ gold snapshot) as a Hugging Face dataset; dataset-push re-uploads
#   make all                       bronze → verify → silver → gold → report → dashboard
#   make show                      row counts, run_labels and source files per bronze table
#   make check-secrets             scan tracked + staged files for credentials (also runs in the pre-commit hook)
#   make hooks                     point git at .githooks/ so check-secrets runs on every commit
#   make test                      all tests, incl. the slow end-to-end snapshot scenarios (5–10 min, needs Java)
#   make test-fast                 the quick tests only (redaction, landing manifest)
#   make clean                     delete data/lakehouse/ (landing is kept; it is the committed input)
#
# Snowflake backend (second backend over the same data/landing/; snowflake/README.md):
#   make sf-setup                  one-time: .venv-sf (snowflake-connector + dbt-snowflake), run snowflake/setup.sql
#   make sf-bronze [RUN_LABEL=...] PUT landing → @LANDING, COPY INTO bronze, FLATTEN the JSON docs, write the ledger
#   make sf-verify                 row counts per (file, table) vs. plain-Python counts of the landed files
#   make sf-silver-gold            dbt seed + dbt build (silver, gold, and every dbt test)
#   make sf-parity                 Snowflake gold vs. space/data/gold.json (the Spark gold export) → docs/parity_report.md
#   make sf-all                    sf-bronze → sf-verify → sf-silver-gold → sf-parity
#   make sf-show                   bronze rows / files / ledger (+ stage listing with SF_SHOW_STAGE=1)
#   Every sf-* target also tees its output to snowflake/logs/<target>.log.
#
# Overrides:  EMBERSERVE_DIR, PULSE_DIR (source roots), FORMAT=delta|parquet, RUN_LABEL

SHELL          := /bin/bash
PY             ?= python3
VENV           ?= .venv
PYTHON         := $(VENV)/bin/python
PIP            := $(VENV)/bin/pip

EMBERSERVE_DIR ?= $(shell [ -d $(HOME)/emberserve ] && echo $(HOME)/emberserve || echo $(HOME)/pagedserve)
PULSE_DIR      ?= $(HOME)/Pulse
FORMAT         ?= delta
RUN_LABEL      ?= $(shell date -u +%Y-%m-%dT%H%MZ)

# Java: Spark 3.5 wants 11/17 (21 works for local mode). Homebrew's openjdk@17 is keg-only, so macOS's
# java_home does not see it unless symlinked; fall back to brew's prefix. Linux: whatever `java` is on PATH.
JAVA_HOME ?= $(shell /usr/libexec/java_home -v 17 2>/dev/null || brew --prefix openjdk@17 2>/dev/null)
ifneq ($(strip $(JAVA_HOME)),)
export JAVA_HOME
export PATH := $(JAVA_HOME)/bin:$(PATH)
endif

# Quiets "hostname resolves to a loopback address" on laptops. (Comment on its own line: make keeps the
# whitespace before an inline # as part of the value.)
export SPARK_LOCAL_IP ?= 127.0.0.1

.PHONY: sf-setup sf-bronze sf-verify sf-silver-gold sf-parity sf-all sf-show sf-dbt-test sf-clean setup land bronze verify silver gold report dashboard space space-login space-create space-push space-create-docker space-push-docker dataset-create dataset-push all show check-secrets hooks test test-fast clean java-check python-check

setup: python-check $(VENV)/.installed java-check

$(VENV)/.installed: requirements.txt
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip >/dev/null
	$(PIP) install -r requirements.txt
	@touch $@

# pyarrow 25 / pyspark 3.5.9 need Python >= 3.10; macOS's Xcode CLT python3 is 3.9 and `make setup` would die inside pip.
python-check:
	@$(PY) -c 'import sys; ok = sys.version_info >= (3, 10); print(f"python: {sys.version.split()[0]} ({sys.executable})"); sys.exit(0 if ok else 1)' \
	  || { echo "need Python 3.10+ (brew install python@3.12, then: make setup PY=python3.12)"; exit 1; }

java-check:
	@command -v java >/dev/null 2>&1 || { \
	  echo "java not found. brew install openjdk@17, then either:"; \
	  echo "  export JAVA_HOME=\"\$$(brew --prefix openjdk@17)\"; export PATH=\"\$$JAVA_HOME/bin:\$$PATH\"   (add to ~/.zshrc)"; \
	  echo "  or once: sudo ln -sfn \"\$$(brew --prefix openjdk@17)/libexec/openjdk.jdk\" /Library/Java/JavaVirtualMachines/openjdk-17.jdk"; \
	  exit 1; }
	@java -version 2>&1 | grep -qE 'version "(11|17|21)' \
	  || { java -version 2>&1 | grep -m1 version; echo "need Java 11, 17 or 21 for Spark 3.5"; exit 1; }
	@echo "java: $$(java -version 2>&1 | grep -m1 version)   JAVA_HOME=$(JAVA_HOME)"

land: $(VENV)/.installed
	$(PYTHON) -m lakehouse.land --emberserve "$(EMBERSERVE_DIR)" --pulse "$(PULSE_DIR)"

bronze: $(VENV)/.installed java-check
	$(PYTHON) -m lakehouse.bronze --run-label "$(RUN_LABEL)" --format $(FORMAT)

verify: $(VENV)/.installed java-check
	$(PYTHON) -m lakehouse.verify --format $(FORMAT)

silver: $(VENV)/.installed java-check
	$(PYTHON) -m lakehouse.silver --format $(FORMAT)

gold: $(VENV)/.installed java-check
	$(PYTHON) -m lakehouse.gold --format $(FORMAT)

report: $(VENV)/.installed java-check
	$(PYTHON) -m lakehouse.report --format $(FORMAT)

dashboard: $(VENV)/.installed java-check
	$(PYTHON) -m lakehouse.dashboard --format $(FORMAT)

SPACE_VENV ?= .venv-space
$(SPACE_VENV)/.installed: space/requirements.txt
	$(PY) -m venv $(SPACE_VENV)
	$(SPACE_VENV)/bin/pip install --upgrade pip >/dev/null
	$(SPACE_VENV)/bin/pip install -r space/requirements.txt
	@touch $@

space: $(SPACE_VENV)/.installed
	cd space && ../$(SPACE_VENV)/bin/streamlit run app.py

$(SPACE_VENV)/bin/hf: $(SPACE_VENV)/.installed
	$(SPACE_VENV)/bin/pip install -q "huggingface_hub>=1.0,<2"

space-login: $(SPACE_VENV)/bin/hf
	$(SPACE_VENV)/bin/hf auth login

# Hosting on huggingface.co: static Spaces are free; Docker/Gradio Spaces on cpu-basic need HF PRO (402 otherwise).
# The static Space is docs/dashboard.html served as index.html — same gold snapshot the Streamlit app reads.
space-create: $(SPACE_VENV)/bin/hf
	@[ -n "$(HF_SPACE)" ] || { echo "usage: make space-create HF_SPACE=<hf-username>/serverless-lakehouse  (after make space-login)"; exit 1; }
	$(SPACE_VENV)/bin/hf repos create "$(HF_SPACE)" --type space --sdk static --public --exist-ok
	$(MAKE) space-push HF_SPACE="$(HF_SPACE)"
	@echo "Space: https://huggingface.co/spaces/$(HF_SPACE)"

space-push: $(SPACE_VENV)/bin/hf docs/dashboard.html
	@[ -n "$(HF_SPACE)" ] || { echo "usage: make space-push HF_SPACE=<hf-username>/serverless-lakehouse  (needs make space-login or HF_TOKEN)"; exit 1; }
	cp docs/dashboard.html space-static/index.html
	$(SPACE_VENV)/bin/hf upload "$(HF_SPACE)" space-static . --repo-type space --commit-message "sync from local $$(git rev-parse --short HEAD)"

# The Streamlit app, for an account with HF PRO: Docker SDK, space/Dockerfile serves on 7860 (space/README.md carries sdk/app_port).
space-create-docker: $(SPACE_VENV)/bin/hf
	@[ -n "$(HF_SPACE)" ] || { echo "usage: make space-create-docker HF_SPACE=<hf-username>/serverless-lakehouse-app"; exit 1; }
	$(SPACE_VENV)/bin/hf repos create "$(HF_SPACE)" --type space --sdk docker --public --exist-ok
	$(MAKE) space-push-docker HF_SPACE="$(HF_SPACE)"

space-push-docker: $(SPACE_VENV)/bin/hf
	@[ -n "$(HF_SPACE)" ] || { echo "usage: make space-push-docker HF_SPACE=<hf-username>/serverless-lakehouse-app"; exit 1; }
	$(SPACE_VENV)/bin/hf upload "$(HF_SPACE)" space . --repo-type space --commit-message "sync from local $$(git rev-parse --short HEAD)"

# The landing zone as a public dataset: dataset/README.md is the card, landing/ is data/landing byte for byte, gold/ the
# committed gold snapshot. Staged into .dataset-stage/ (gitignored) because the card must not live inside the landing
# mirror (`make land` prunes anything the manifest does not list). --delete keeps the remote a mirror after renames.
HF_DATASET ?= ashwin-sreedhar/runpod-serverless-benchmarks
dataset-create: $(SPACE_VENV)/bin/hf
	$(SPACE_VENV)/bin/hf repos create "$(HF_DATASET)" --type dataset --public --exist-ok
	$(MAKE) dataset-push HF_DATASET="$(HF_DATASET)"
	@echo "Dataset: https://huggingface.co/datasets/$(HF_DATASET)"

dataset-push: $(SPACE_VENV)/bin/hf
	rm -rf .dataset-stage && mkdir -p .dataset-stage/gold
	cp dataset/README.md .dataset-stage/README.md
	cp -R data/landing .dataset-stage/landing
	cp docs/gold_report.md space/data/gold.json .dataset-stage/gold/
	$(SPACE_VENV)/bin/hf upload "$(HF_DATASET)" .dataset-stage . --repo-type dataset --delete "landing/*" --delete "gold/*" \
	  --commit-message "sync from local $$(git rev-parse --short HEAD)"

all: bronze verify silver gold report dashboard

show: $(VENV)/.installed java-check
	$(PYTHON) -m lakehouse.show --format $(FORMAT)

check-secrets: $(VENV)/.installed
	$(PYTHON) scripts/check_secrets.py

hooks:
	git config core.hooksPath .githooks
	@echo "pre-commit hook active: .githooks/pre-commit"

test: $(VENV)/.installed
	$(PYTHON) -m pytest -q tests

test-fast: $(VENV)/.installed
	$(PYTHON) -m pytest -q tests -m "not slow"

clean:
	rm -rf data/lakehouse spark-warehouse metastore_db derby.log

# ------------------------------------------------------------------------------------------------------------------
# Snowflake backend. Credentials come from snowflake/.env (gitignored; see snowflake/.env.example): the Python loader
# and dbt read the same variables. Separate venv so the Spark pins and the connector/dbt pins never fight.
# ------------------------------------------------------------------------------------------------------------------
SF_VENV   ?= .venv-sf
SF_PYTHON := $(SF_VENV)/bin/python
SF_DBT    := $(SF_VENV)/bin/dbt
SF_LOGS   := snowflake/logs
-include snowflake/.env
export SNOWFLAKE_ACCOUNT SNOWFLAKE_USER SNOWFLAKE_PRIVATE_KEY_PATH SNOWFLAKE_PRIVATE_KEY_PASSPHRASE SNOWFLAKE_ROLE SNOWFLAKE_WAREHOUSE SNOWFLAKE_DATABASE
# dbt does not expand ~ in private_key_path
SNOWFLAKE_PRIVATE_KEY_PATH ?= $(HOME)/.snowflake/lakehouse_rsa_key.p8
export SNOWFLAKE_PRIVATE_KEY_PATH := $(subst ~,$(HOME),$(SNOWFLAKE_PRIVATE_KEY_PATH))

$(SF_VENV)/.installed: snowflake/requirements.txt
	$(PY) -m venv $(SF_VENV)
	$(SF_VENV)/bin/pip install --upgrade pip >/dev/null
	$(SF_VENV)/bin/pip install -r snowflake/requirements.txt
	@touch $@

$(SF_LOGS):
	mkdir -p $(SF_LOGS)

sf-setup: python-check $(SF_VENV)/.installed $(SF_LOGS)
	@[ -f snowflake/.env ] || { echo "snowflake/.env missing: cp snowflake/.env.example snowflake/.env and fill it in"; exit 1; }
	$(SF_PYTHON) -m lakehouse.sf.setup 2>&1 | tee $(SF_LOGS)/sf-setup.log; exit $${PIPESTATUS[0]}
	cd snowflake/dbt && ../../$(SF_DBT) debug --no-use-colors 2>&1 | tee ../../$(SF_LOGS)/dbt-debug.log; exit $${PIPESTATUS[0]}

sf-bronze: $(SF_VENV)/.installed $(SF_LOGS)
	$(SF_PYTHON) -m lakehouse.sf.bronze --run-label "$(RUN_LABEL)" $(SF_BRONZE_FLAGS) 2>&1 | tee $(SF_LOGS)/sf-bronze.log; exit $${PIPESTATUS[0]}

sf-verify: $(SF_VENV)/.installed $(SF_LOGS)
	$(SF_PYTHON) -m lakehouse.sf.verify 2>&1 | tee $(SF_LOGS)/sf-verify.log; exit $${PIPESTATUS[0]}

sf-silver-gold: $(SF_VENV)/.installed $(SF_LOGS)
	cd snowflake/dbt && ../../$(SF_DBT) seed --no-use-colors 2>&1 | tee ../../$(SF_LOGS)/dbt-seed.log; exit $${PIPESTATUS[0]}
	cd snowflake/dbt && ../../$(SF_DBT) build --no-use-colors $(DBT_FLAGS) 2>&1 | tee ../../$(SF_LOGS)/dbt-build.log; exit $${PIPESTATUS[0]}

sf-dbt-test: $(SF_VENV)/.installed $(SF_LOGS)
	cd snowflake/dbt && ../../$(SF_DBT) test --no-use-colors $(DBT_FLAGS) 2>&1 | tee ../../$(SF_LOGS)/dbt-test.log; exit $${PIPESTATUS[0]}

sf-parity: $(SF_VENV)/.installed $(SF_LOGS)
	$(SF_PYTHON) -m lakehouse.sf.parity 2>&1 | tee $(SF_LOGS)/sf-parity.log; exit $${PIPESTATUS[0]}

sf-show: $(SF_VENV)/.installed $(SF_LOGS)
	$(SF_PYTHON) -m lakehouse.sf.show $(if $(SF_SHOW_STAGE),--stage,) 2>&1 | tee $(SF_LOGS)/sf-show.log; exit $${PIPESTATUS[0]}

sf-all: sf-bronze sf-verify sf-silver-gold sf-parity

sf-clean:
	rm -rf snowflake/dbt/target snowflake/dbt/logs snowflake/dbt/dbt_packages

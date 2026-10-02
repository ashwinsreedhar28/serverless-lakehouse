# serverless-lakehouse — bronze/silver/gold over Runpod Serverless benchmark data.
#
#   make setup                     create .venv, install pinned PySpark + Delta, check Java
#   make land                      extract: copy + redact sources into data/landing/ (+ manifest)
#   make bronze [RUN_LABEL=...]    ingest data/landing/ into bronze Delta tables (append-only)
#   make verify                    bronze row counts vs. what the landing manifest says they should be
#   make show                      row counts, run_labels and source files per bronze table
#   make check-secrets             scan tracked + staged files for credentials (also runs in the pre-commit hook)
#   make hooks                     point git at .githooks/ so check-secrets runs on every commit
#   make test                      unit tests (redaction, manifest)
#   make clean                     delete data/lakehouse/ (landing is kept; it is the committed input)
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

.PHONY: setup land bronze verify show check-secrets hooks test clean java-check

setup: $(VENV)/.installed java-check

$(VENV)/.installed: requirements.txt
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip >/dev/null
	$(PIP) install -r requirements.txt
	@touch $@

java-check:
	@java -version 2>&1 | grep -E 'version "(11|17|21)' >/dev/null \
	  || { echo "need Java 11/17/21 on PATH (brew install openjdk@17; export JAVA_HOME=\$$(/usr/libexec/java_home -v 17))"; exit 1; }
	@java -version 2>&1 | head -1

land: $(VENV)/.installed
	$(PYTHON) -m lakehouse.land --emberserve "$(EMBERSERVE_DIR)" --pulse "$(PULSE_DIR)"

bronze: $(VENV)/.installed
	$(PYTHON) -m lakehouse.bronze --run-label "$(RUN_LABEL)" --format $(FORMAT)

verify: $(VENV)/.installed
	$(PYTHON) -m lakehouse.verify --format $(FORMAT)

show: $(VENV)/.installed
	$(PYTHON) -m lakehouse.show --format $(FORMAT)

check-secrets: $(VENV)/.installed
	$(PYTHON) scripts/check_secrets.py

hooks:
	git config core.hooksPath .githooks
	@echo "pre-commit hook active: .githooks/pre-commit"

test: $(VENV)/.installed
	$(PYTHON) -m pytest -q tests

clean:
	rm -rf data/lakehouse spark-warehouse metastore_db derby.log

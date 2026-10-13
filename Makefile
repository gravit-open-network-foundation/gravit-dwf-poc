VERIFIER_TAG := v0.6.0
PYTHON ?= python3
PY := .venv/bin/python

setup:
	$(PYTHON) -m venv .venv
	[ -d .deps/verifier ] || git -c advice.detachedHead=false clone -q --depth 1 --branch $(VERIFIER_TAG) https://github.com/gravit-open-network-foundation/verifier.git .deps/verifier
	$(PY) -m pip install -q -e .deps/verifier pytest

run:
	$(PY) -m scenarios.run

test:
	$(PY) -m pytest -q

.PHONY: setup run test

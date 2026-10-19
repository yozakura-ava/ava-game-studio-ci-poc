PYTHON ?= python3

.PHONY: setup validate lint test build clean

## setup — install the pre-push publish gate into .git/hooks (run once per clone)
setup:
	@cp publish/hooks/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push
	@echo "pre-push publish gate installed"

## validate — allowlist-first content gate over the working tree
validate:
	$(PYTHON) publish/publish_gate.py --mode tree

## lint — gate + syntax compile of all first-party python
lint: validate
	$(PYTHON) -m compileall -q src publish scripts

## test — real unit tests (stdlib unittest, zero dependencies)
test:
	$(PYTHON) -m unittest discover -s tests -v

## build — package the PoC bundle artifact (dist/)
build:
	$(PYTHON) scripts/package.py

clean:
	rm -rf dist src/__pycache__ tests/__pycache__ publish/__pycache__ scripts/__pycache__

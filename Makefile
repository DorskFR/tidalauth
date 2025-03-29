# Makefile
PYTHON ?= ./.venv/bin/python
APP ?= tidalauth

%:
	@:

setup:
	rye sync

make setup/playwright:
	$(PYTHON) -m playwright install --with-deps

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} \;
	find . -type d -name .cache -prune -exec rm -rf {} \;
	find . -type d -name .mypy_cache -prune -exec rm -rf {} \;
	find . -type d -name .pytest_cache -prune -exec rm -rf {} \;
	find . -type d -name .ruff_cache -prune -exec rm -rf {} \;
	find . -type d -name .venv -prune -exec rm -rf {} \;

clear:
	rm -rf videos/*

lint:
	$(PYTHON) -m ruff check ./$(APP) $(TESTS)
	$(PYTHON) -m ruff format --check ./$(APP) $(TESTS)
	$(PYTHON) -m mypy ./$(APP) $(TESTS)
	$(PYTHON) -m vulture --min-confidence=100 ./$(APP) $(TESTS)

fmt:
	$(PYTHON) -m ruff check --fix-only ./$(APP) $(TESTS)
	$(PYTHON) -m ruff format ./$(APP) $(TESTS)

run:
	$(PYTHON) -m $(APP)

.PHONY: $(shell grep -E '^([a-zA-Z_-]|\/)+:' $(MAKEFILE_LIST) | awk -F':' '{print $$2}' | sed 's/:.*//')

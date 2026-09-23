PYTHON ?= python3
.PHONY: all test clean official stages zip
all:
	$(PYTHON) tools/build.py final
	$(PYTHON) tools/report.py
official:
	$(PYTHON) tools/build.py official
test:
	$(PYTHON) tools/check_sources.py
	$(PYTHON) tests/run.py
	$(PYTHON) tests/w5500.py
	$(PYTHON) tests/link_limit.py
	$(PYTHON) tests/application_build.py
stages:
	$(PYTHON) tools/stages.py
zip: all test
	$(PYTHON) tools/package.py
clean:
	$(PYTHON) tools/clean.py

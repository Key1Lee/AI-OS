.PHONY: check test validate start

check: validate test

validate:
	python3 -m semantic validate

test:
	python3 -m unittest discover -s tests -v

start:
	python3 -m semantic scenario SEM-REVENUE-001

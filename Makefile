.DEFAULT_GOAL := help
export RATE DURATION SEED BATCH_SIZE SAVEPOINT CONFIRM
# Environment overrides have defaults in .env; do not export unset make variables.
unexport RATE DURATION SEED BATCH_SIZE SAVEPOINT CONFIRM
ifdef RATE
export RATE
endif
ifdef DURATION
export DURATION
endif
ifdef SEED
export SEED
endif
ifdef BATCH_SIZE
export BATCH_SIZE
endif
ifdef SAVEPOINT
export SAVEPOINT
endif
ifdef CONFIRM
export CONFIRM
endif
.PHONY: help doctor init build up bootstrap seed submit status demo generate query test-unit test-e2e savepoint stop-with-savepoint restore logs down reset reconcile finite stress-up superset-up superset-status superset-down
help:
	@echo 'First run: make init doctor build demo | docs: README.md'
doctor init build up bootstrap seed submit status demo generate query savepoint stop-with-savepoint restore logs down reset reconcile finite superset-up superset-status superset-down:
	python3 scripts/lab.py $@
test-unit:
	./mvnw -B -ntp test
	python3 -m unittest discover -s tests -p 'test_*.py'
test-e2e:
	bash scripts/test-e2e.sh
stress-up:
	COMPOSE_FILE=compose.yaml:compose.stress.yaml bash scripts/stress.sh

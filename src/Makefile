.PHONY: server client storage

pyfiles := $(wildcard ffserver/*.py common/*.py client/*.py)

build: storage
	$(NOOP)

storage:
	$(MAKE) -C storage

# just for me for developing
server: $(pyfiles)
	bash ~/scripts/runwatch.sh "python -m ffserver" $^

# just for me for developing
client: $(pyfiles)
	bash ~/scripts/runwatch.sh "python -m client new maps/smallmap.json" $^

run-server:
	python -m ffserver localhost

run-client:
	python -m client new maps/smallmap.json

ffserver/%.py:
	$(NOOP)

client/%.py:
	$(NOOP)

common/%.py:
	$(NOOP)

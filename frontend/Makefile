
SHELL:=/bin/bash
HOST:=$(shell hostname -I | awk '{print $$1}')
.PHONY: host
host:
	@echo "$(HOST)"

.PHONY: serve
serve:
	export PYTHONPATH=../daedalus; \
		python3.8 -m daedalus serve \
			--env baseUrl='http://$(HOST):4200' \
			--static ./resources \
			src/app.js

.PHONY: build
build:
	export PYTHONPATH=../daedalus; python3.8 -m daedalus build --static ./resources src/app.js ./build

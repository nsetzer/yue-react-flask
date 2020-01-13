
SHELL:=/bin/bash
HOST:=$(shell hostname -I | awk '{print $$1}')
DATE:=$(shell date +'%F %T')
.PHONY: host
host:
	@echo "$(HOST)"

.PHONY: serve
serve:
	export PYTHONPATH=../daedalus; \
		python3.8 -m daedalus serve \
			--env baseUrl='http://$(HOST):4200' \
			--env buildDate="$(DATE)" \
			--static ./resources \
			src/app.js

.PHONY: build
build:
	export PYTHONPATH=../daedalus; \
		python3.8 -m daedalus build \
		--env buildDate="$(DATE)" \
		--static ./resources \
		src/app.js ./build


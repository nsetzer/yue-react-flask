
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

.PHONY: serve_prod
serve_prod:
	export PYTHONPATH=../daedalus; \
		python3.8 -m daedalus serve \
			--env baseUrl='https://yueapp.duckdns.org' \
			--env buildDate="$(DATE)" \
			--static ./resources \
			src/app.js

.PHONY: build_debug
build_debug:
	export PYTHONPATH=../daedalus; \
		python3.8 -m daedalus build \
		--env buildDate="$(DATE)" \
		--static ./resources \
		src/app.js ./build

.PHONY: build
build:
	export PYTHONPATH=../daedalus; \
		python3.8 -m daedalus build \
		--env buildDate="$(DATE)" \
		--static ./resources \
		--minify \
		src/app.js ./build

.PHONY: build_html
build_html:
	export PYTHONPATH=../daedalus; \
		python3.8 -m daedalus build \
		--env buildDate="$(DATE)" \
		--static ./resources \
		--minify \
		--onefile \
		src/app.js ./build


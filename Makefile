
SHELL := /bin/bash

.PHONY: serve_dev
serve_dev:
	source venv/bin/activate && python -m yueserver.app -p development
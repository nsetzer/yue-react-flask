

base:
	docker build -t yueapp/base -f util/Dockerfile-Base .

build:
	docker build -t yueapp/server -f util/Dockerfile-Server .

run:
	docker run -d -p 1080:4200 -p 5431:5432 --name yueapp-server yueapp/server

start:
	docker start yueapp-postgres

stop:
	docker stop yueapp-postgres

delete:
	docker stop yueapp-postgres
	docker container rm yueapp-postgres

connect:
	docker exec -it  yueapp-postgres /bin/bash

bash:
	docker run -it yueapp/server /bin/bash

logs:
	docker logs -f yueapp-postgres

clean:
	find . -name "*.pyc" | xargs rm
	find . -name "__pycache__" | xargs rm -r
	rm -r build dist htmlcov temp venv

help:
	@grep '^[^#[:space:]].*:$$' Makefile | tr -d ':' | sort

.PHONY: init build run start stop delete connect logs clean help bash


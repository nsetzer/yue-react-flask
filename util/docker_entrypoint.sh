#!/bin/bash


/etc/init.d/postgresql start

python3 -m yueserver.app -p docker


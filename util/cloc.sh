#!/bin/bash

cloc --not-match-f='.*_test.py' ./server 2>&1 | \
    grep -B 3 -e Python | \
    sed 's=Python          =Python w/o Tests='
cloc ./server 2>&1 | grep -A 1 Python

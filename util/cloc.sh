#!/bin/bash

msg=$(cloc --not-match-f='.*_test.py' ./yueserver 2>&1 | \
    grep -B 3 -e Python | \
    sed 's=Python          =Python w/o Tests=')
cnt=$(echo "$msg" | tail -n 1 | awk '{print $5 + $6 + $7}')
echo "$msg - $cnt"

msg=$(cloc ./yueserver 2>&1 | grep Python)
cnt=$(echo "$msg" | awk '{print $3 + $4 + $5}')
echo "$msg - $cnt"

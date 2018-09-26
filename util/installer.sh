#!/bin/bash
echo ""
echo "Self Extracting Installer"
echo ""

EXTRACT_DIR=${1:-/opt/yueserver}

if [ ! -e "$EXTRACT_DIR" ];
then
    mkdir -p "$EXTRACT_DIR"
fi

ARCHIVE=`awk '/^__ARCHIVE_BELOW__/ {print NR + 1; exit 0; }' $0`
tail -n+$ARCHIVE $0 | tar -xzv -C $EXTRACT_DIR

if id yueapp &> /dev/null;
then
    pushd "$PWD"

    chown yueapp .
    chown -R yueapp $(echo * | sed s/crypt//)

    chgrp yueapp .
    chgrp -R yueapp $(echo * | sed s/crypt//)

    popd
fi

exit 0

__ARCHIVE_BELOW__

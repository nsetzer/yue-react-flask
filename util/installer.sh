#!/bin/bash
echo ""
echo "Self Extracting Installer"
echo ""

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

EXTRACT_DIR=${1:-/opt/yueserver}

if [ ! -e "$EXTRACT_DIR" ];
then
    mkdir -p "$EXTRACT_DIR"
fi

cd "$EXTRACT_DIR"

if [ -e "./uninstall.sh" ]; then
    ./uninstall.sh
fi

echo "install yueserver to $EXTRACT_DIR"
ARCHIVE=`awk '/^__ARCHIVE_BELOW__/ {print NR + 1; exit 0; }' $0`
tail -n+$ARCHIVE $0 | tar -xz

if id yueapp &> /dev/null;
then
    chown yueapp .
    chown -R yueapp $(echo * | sed s/crypt//)

    chgrp yueapp .
    chgrp -R yueapp $(echo * | sed s/crypt//)
fi

exit 0

__ARCHIVE_BELOW__

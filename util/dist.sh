
version=0.0.0

mkdir -p dist

cat <<EOF > start.sh
#!/bin/bash
cd \$(dirname \$0)
echo \$PWD
gunicorn=/opt/yueserver/yueserverenv/bin/gunicorn
user=\$(stat -c '%U' wsgi.py)
YUE_PRIVATE_KEY=\$(cat ./crypt/rsa.pem)
export YUE_PRIVATE_KEY
exec sudo -u "\$user" "\$gunicorn" -p"\${1:-production}" -w 2 --bind unix:yueserver.sock wsgi:app
EOF

cat <<EOF > uninstall.sh
#!/bin/bash
rm -rf server client build wsgi.py requirements.txt
EOF

cat <<EOF > post_install.sh
#!/bin/bash

chown yueapp .
chown -R yueapp \$(echo * | sed s/crypt//)

chgrp yueapp .
chgrp -R yueapp \$(echo * | sed s/crypt//)

EOF

chmod +x start.sh
chmod +x uninstall.sh
chmod +x post_install.sh

python3 -m server.tools.manage generate_client

tar -czvf dist/yueserver-$version.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    config server client build wsgi.py requirements.txt \
    start.sh uninstall.sh post_install.sh

rm start.sh
rm uninstall.sh
rm post_install.sh


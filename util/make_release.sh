
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
exec sudo -E -u "\$user" "\$gunicorn" -p"\${1:-production}" -w 2 --bind unix:yueserver.sock wsgi:app
EOF

cat <<EOF > uninstall.sh
#!/bin/bash
echo "uninstalling yueserver"
rm -rf yueserver yueclient build wsgi.py requirements.txt
EOF

chmod +x start.sh
chmod +x uninstall.sh

python3 -m yueserver.tools.manage generate_client

tar -czv --exclude='*.pyc' --exclude='__pycache__' \
    config yueserver yueclient build wsgi.py requirements.txt setup.py \
    start.sh uninstall.sh | \
    cat util/installer.sh - > dist/yueserver-$version.tar.gz

rm start.sh
rm uninstall.sh


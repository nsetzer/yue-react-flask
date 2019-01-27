
version=0.0.0
githash=$(git rev-parse HEAD)
branch=$(git rev-parse --abbrev-ref HEAD)
mkdir -p dist

cat <<EOF > start.sh
#!/bin/bash
cd \$(dirname \$0)
echo \$PWD
gunicorn=/opt/yueserver/yueserverenv/bin/gunicorn
user=\$(stat -c '%U' wsgi.py)
YUE_PRIVATE_KEY=\$(cat ./crypt/rsa.pem)
export YUE_PRIVATE_KEY
exec sudo -E -u "\$user" "\$gunicorn" -p"\${1:-production}" --worker-class eventlet -w 1 --bind unix:yueserver.sock wsgi:app
EOF

cat <<EOF > start_debug.sh
#!/bin/bash
cd \$(dirname \$0)
echo \$PWD
user=\$(stat -c '%U' wsgi.py)
YUE_PRIVATE_KEY=\$(cat ./crypt/rsa.pem)
export YUE_PRIVATE_KEY
exec sudo -E -u "\$user" python3 wsgi.py -p"\${1:-production}"
EOF

cat <<EOF > uninstall.sh
#!/bin/bash
echo "uninstalling yueserver"
rm -rf yueserver yueclient build wsgi.py requirements.txt
EOF

chmod +x start.sh
chmod +x uninstall.sh

cat << EOF > yueserver/__init__.py
__version__ = '$version'
__branch__ = '$branch'
__githash__ = '$githash'
EOF

tar -czv --exclude='*.pyc' --exclude='__pycache__' \
    config yueserver res wsgi.py requirements.txt setup.py \
    start.sh start_debug.sh uninstall.sh | \
    cat util/installer.sh - > dist/yueserver-$version.tar.gz

rm start.sh
rm start_debug.sh
rm uninstall.sh

echo "$version $branch $githash"

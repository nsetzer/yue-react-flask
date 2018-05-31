
version=0.0.0

mkdir -p dist

cat <<EOF > start.sh
#!/bin/bash
cd \$(dirname $0)
echo $PWD
exec python3 ./wsgi.py -p production
EOF

python3 -m server.tools.manage generate_client

tar -czvf dist/yueserver-$version.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    config server client build wsgi.py start.sh

rm start.sh


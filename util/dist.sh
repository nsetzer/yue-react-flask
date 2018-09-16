
version=0.0.0

mkdir -p dist

cat <<EOF > start.sh
#!/bin/bash
cd \$(dirname \$0)
echo \$PWD
gunicorn=\$(which gunicorn)
user=\$(stat -c '%U' wsgi.py)
exec sudo -u "\$user" "\$gunicorn" -w 1 wsgi:app < ./crypto/rsa.pem
EOF

python3 -m server.tools.manage generate_client

tar -czvf dist/yueserver-$version.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    config server client build wsgi.py requirements.txt start.sh

# rm start.sh



version=0.0.0
githash=$(git rev-parse HEAD)
branch=$(git rev-parse --abbrev-ref HEAD)
mkdir -p dist

cat <<EOF > backupdb.sh
#!/bin/bash
# backup:
# $0 $profile $dbuser $bucket
# restore:
# cat backup/backup-\$(date "+%y-%m-%d-%H-%M-%S").gz.* | gunzip | sudo -u yueapp psql yueapp

if [ "$#" -ne 3 ];
    echo "$0 profile dbuser bucket"
fi

cd \$(dirname \$0)
profile=\$1
dbuser=\$2
bucket=\$3
source yueserverenv/bin/activate
YUE_PRIVATE_KEY=\$(cat ./crypt/rsa.pem)
export YUE_PRIVATE_KEY

mkdir backup
sudo -u \$dbuser pg_dump \$dbuser | gzip | split -d -b 512M - backup/backup-\$(date "+%y-%m-%d-%H-%M-%S").gz.
python -m yueserver.tools.manage -p\$profile fs cp backup/* "s3://\$bucket/backups/\$(date "+%y-%m-%d")/"
rm -rf backup

EOF

cat <<EOF > manage.sh
#!/bin/bash
cd \$(dirname \$0)
source yueserverenv/bin/activate
YUE_PRIVATE_KEY=\$(cat ./crypt/rsa.pem)
export YUE_PRIVATE_KEY
echo python -m yueserver.tools.manage \$@
python -m yueserver.tools.manage \$@
EOF

cat <<EOF > start.sh
#!/bin/bash
cd \$(dirname \$0)
echo \$PWD
gunicorn=/opt/yueserver/yueserverenv/bin/gunicorn
user=\$(stat -c '%U' wsgi.py)
YUE_PRIVATE_KEY=\$(cat ./crypt/rsa.pem)
export YUE_PRIVATE_KEY
exec sudo -E -u "\$user" "\$gunicorn" -t 240 -p"\${1:-production}" -w 2 --bind unix:yueserver.sock wsgi:app
EOF

cat <<EOF > start_debug.sh
#!/bin/bash
cd \$(dirname \$0)
echo \$PWD
user=\$(stat -c '%U' wsgi.py)
YUE_PRIVATE_KEY=\$(cat ./crypt/rsa.pem)
export YUE_PRIVATE_KEY
cat /etc/letsencrypt/live/yueapp.duckdns.org/fullchain.pem > "config/\${1:-production}/fullchain.pem"
cat /etc/letsencrypt/live/yueapp.duckdns.org/privkey.pem > "config/\${1:-production}/privkey.pem"

exec sudo -E -u "\$user" python3 wsgi.py -p"\${1:-production}"
EOF

cat <<EOF > uninstall.sh
#!/bin/bash
cd \$(dirname \$0)
echo "uninstalling yueserver"
rm -rf yueserver yueclient build frontend
rm wsgi.py requirements.txt
rm start.sh start_debug.sh uninstall.sh
rm manage.sh backupdb.sh
EOF

chmod +x start.sh
chmod +x uninstall.sh

cat << EOF > yueserver/__init__.py
__version__ = '$version'
__branch__ = '$branch'
__githash__ = '$githash'
__date__ = '$(date '+%Y-%m-%d %H:%M:%S')'
EOF

tar -czv --exclude='*.pyc' --exclude='__pycache__' \
    config yueserver res wsgi.py requirements.txt setup.py frontend/build \
    start.sh start_debug.sh uninstall.sh manage.sh backupdb.sh | \
    cat util/installer.sh - > dist/yueserver-$version.tar.gz

rm manage.sh
rm start.sh
rm start_debug.sh
rm uninstall.sh
rm backupdb.sh

echo "$version $branch $githash"

git checkout yueserver/__init__.py

version=0.0.0

mkdir -p dist


cat <<EOF > start.sh
#!/bin/bash
cd `dirname $0`
echo $PWD
exec python3 ./app.py --config config/production/application.yml
EOF

tar -cvf dist/yueserver-$version.tar *.py config server build

rm start.sh


HOST="http://localhost:4200"
#############################################################
# create a new application database
# start the server and wait for it to be ready to
# accept connections
python -m yueserver.tools.manage -p development create
python -m yueserver.app -pdevelopment 2>server.err 1>server.log &
APP_PID=$!
trap "kill $APP_PID" SIGINT SIGTERM EXIT
echo "waiting for server to start"
sleep 10

#############################################################
# test syncing

rm -rf sync1 sync2 sync3

mkdir sync2
pushd sync2

python ../sync2.py init -u admin -p admin "$HOST"

mkdir secure private public

cat << EOF > .yueattr
[settings]
encryption_mode=none
public=False

[blacklist]
*.pyc
__pycache__
EOF

# cat << EOF > secure/.yueattr
# [settings]
# encryption_mode=client
# public=False
# EOF
#
# cat << EOF > private/.yueattr
# [settings]
# encryption_mode=server
# public=False
# EOF

cat << EOF > public/.yueattr
[settings]
encryption_mode=system
public=False
EOF

python ../sync2.py push -r

popd

mkdir sync3
pushd sync3

python ../sync2.py init -u admin -p admin -r public "$HOST"

echo "test file" > test

python ../sync2.py sync -u -r

popd
pushd sync2

python ../sync2.py sync -u -r

popd

#############################################################
# test syncing

function die() {
    echo $1
    exit 1
}

function assert_fexists() {
    [ -e "$1" ] && echo "found: $1" || die "not found: $1"
}

assert_fexists sync2/public/.yueattr
assert_fexists sync2/public/test

assert_fexists sync3/.yueattr
assert_fexists sync3/test
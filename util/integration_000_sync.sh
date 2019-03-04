

# usage:
#   bash -e util/integration_000_sync.sh < /dev/null
# force the test to fail if any command fails or if
# a command requires input
HOST="http://localhost:4200"


function die() {
    echo $1
    exit 1
}

function assert_fequal() {
    f1=$(cat $1 | md5sum | awk {'print $1'})
    f2=$(cat $1 | md5sum | awk {'print $1'})
    [ "$f1" == "$f2" ] && echo "match: $1" || die "not equal: $1 $2"
}

function assert_fexists() {
    [ -e "$1" ] && echo "found: $1" || die "not found: $1"
}


#############################################################
# create a new application database
# start the server and wait for it to be ready to
# accept connections
python -m yueserver.tools.manage -p development create
python -m yueserver.app -pdevelopment 2>server.err 1>server.log &
APP_PID=$!
trap "kill $APP_PID" SIGINT SIGTERM EXIT
echo "waiting for server to start"
sleep 3

#############################################################
# test 1: syncing, partial checkouts

rm -rf sync1 sync2 sync3 sync4

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

assert_fexists sync2/public/.yueattr
assert_fexists sync2/public/test

assert_fexists sync3/.yueattr
assert_fexists sync3/test

assert_fequal sync2/public/.yueattr sync3/.yueattr
assert_fequal sync2/public/test sync3/test

#############################################################
# Test 2: encryption

pushd sync2

cat << EOF > secure/.yueattr
[settings]
encryption_mode=client
public=False
EOF

cat << EOF > private/.yueattr
[settings]
encryption_mode=server
public=False
EOF

cat << EOF | python ../sync2.py setpass
password1
password1
EOF

cat << EOF | python ../sync2.py setkey
password2
password2
EOF

echo password1 | python ../sync2.py push private/.yueattr
echo password2 | python ../sync2.py push secure/.yueattr

popd

mkdir sync4
pushd sync4

python ../sync2.py init -u admin -p admin "$HOST"


echo password1 | python ../sync2.py pull private/.yueattr
echo password2 | python ../sync2.py pull secure/.yueattr

assert_fexists private/.yueattr
assert_fexists secure/.yueattr

popd

f1s=$(md5sum sync2/secure/.yueattr)
f1p=$(md5sum sync2/private/.yueattr)

f2s=$(md5sum sync4/secure/.yueattr)
f2p=$(md5sum sync4/private/.yueattr)

assert_fequal sync{2,4}/secure/.yueattr
assert_fequal sync{2,4}/private/.yueattr

echo "success"
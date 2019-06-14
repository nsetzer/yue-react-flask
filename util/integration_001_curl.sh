

# usage:
#   bash -e util/integration_000_sync.sh < /dev/null
# force the test to fail if any command fails or if
# a command requires input
HOST="http://localhost:4200"
AUTH="admin:admin"

function die() {
    echo $1
    exit 1
}

function assert_fequal() {
    f1=$(cat $1 | md5sum | awk {'print $1'})
    f2=$(cat $2 | md5sum | awk {'print $1'})
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
# test setup

api_txt_1="api/fs/default/path/curl/test1.txt"

api_form_1="api/fs/default/path/curl/test1.form"

api_bin_1="api/fs/default/path/curl/test1.bin"
api_bin_2="api/fs/default/path/curl/test2.bin"
api_bin_3="api/fs/default/path/curl/test2.bin?crypt=system"
api_bin_4="api/fs/default/path/curl/test2.bin?crypt=server"

txt_file="./integration_001_curl.sh"
bin_file="./test/r160.mp3"

if [ ! -e "$bin_file" ]; then
    exit 1
fi

out_txt_1="/tmp/test1.txt"
out_form_1="/tmp/test1.form"
out_bin_1="/tmp/test1.bin"
out_bin_2="/tmp/test2.bin"
out_bin_3="/tmp/test3.bin"
out_bin_4="/tmp/test4.bin"

#############################################################
# test 1: text uploads supported with minimal arguments

curl -v -u "$AUTH" -d "@$txt_file" "$HOST/$api_txt_1"
curl -v -u "$AUTH" "$HOST/$api_txt_1" -o "$out_txt_1"
assert_fequal "${txt_file}" "${out_txt_1}"

#############################################################
# test 2: form uploads are saved as raw form data

curl -v -u "$AUTH" -d name=user000 -d role=editor "$HOST/$api_form_1"
curl -v -u "$AUTH" "$HOST/$api_form_1" -o "$out_form_1"
echo -n "name=user000&role=editor" > "${out_form_1}.expected"
assert_fequal "${out_form_1}" "${out_form_1}.expected"

#############################################################
# test 3: binary upload as multipart form
curl -v -u "$AUTH" --data-binary "@$bin_file" "$HOST/$api_bin_1"
curl -v -u "$AUTH" "$HOST/$api_bin_1" -o "$out_bin_1"
assert_fequal "${bin_file}" "${out_bin_1}"

#############################################################
# test 4: streaming binary upload
curl -v -u "$AUTH" -H "Content-Type: application/octet-stream" --data-binary "@$bin_file" "$HOST/$api_bin_2"
curl -v -u "$AUTH" "$HOST/$api_bin_2" -o "$out_bin_2"
assert_fequal "${bin_file}" "${out_bin_2}"

#############################################################
# test 5: streaming binary upload, encrypted
curl -v -u "$AUTH" -H "Content-Type: application/octet-stream" --data-binary "@$bin_file" "$HOST/$api_bin_3" -o "$out_bin_3.upload"
curl -v -u "$AUTH" "$HOST/$api_bin_2" -o "$out_bin_3"
assert_fequal "${bin_file}" "${out_bin_3}"

if cat "$out_bin_3.upload" | grep system; then
    echo "remote file is encrypted...success"
else
    die "remote file not encrypted...failure"
fi

#############################################################
# test 6: streaming binary upload, encrypted
# NOTE: requires setting a key first
# curl -v -u "$AUTH" -H 'X-YUE-PASSWORD: password' -H "Content-Type: application/octet-stream" --data-binary "@$bin_file" "$HOST/$api_bin_4" -o "$out_bin_4.upload"
# curl -v -u "$AUTH" -H 'X-YUE-PASSWORD: password' "$HOST/$api_bin_4" -o "$out_bin_4"
# assert_fequal "${bin_file}" "${out_bin_4}"
#
# if cat "$out_bin_4.upload" | grep server; then
#     echo "remote file is encrypted"
# else
#     die "remote file not encrypted"
# fi

#############################################################
# test 5:
# curl -v -u "$AUTH" -H "Content-Type: application/json" -d '{"key1":"value1", "key2":"value2"}' "$HOST/$api_bin_2"


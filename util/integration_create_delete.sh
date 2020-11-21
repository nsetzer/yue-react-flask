HOST="http://localhost:4200"
AUTH="admin:admin"
VERBOSE="--silent"

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
# test 1:


api_create="api/library"

result=$(curl $VERBOSE -u "$AUTH" \
    -H "Content-Type: application/json" \
    -d '{"artist": "artist", "title": "title", "album": "album"}' \
    "$HOST/$api_create")

SONG_ID=$(echo "$result" | jq .result | tr -d \")
echo "SONG_ID: $SONG_ID"

#############################################################
# test 2:
FS_ROOT="default"
FS_PATH="test.aud"
api_upload="api/fs/$FS_ROOT/path/$FS_PATH"

result=$(curl $VERBOSE -u "$AUTH" \
    -d "{}" \
    "$HOST/$api_upload")

message=$(echo "$result" | jq .result | tr -d \")

if [ "$message" != "OK" ]; then
    echo "error: $result"
    exit 1
else
    echo "success: $result"
fi


#############################################################
# test 3:

api_update="api/library/${SONG_ID}/audio"

touch test.aud
track="{\"root\": \"${FS_ROOT}\", \"path\": \"$PWD/test.aud\"}"

result=$(curl $VERBOSE -u "$AUTH" \
    -H "Content-Type: application/json" \
    -d "{\"root\": \"${FS_ROOT}\", \"path\": \"test.aud\"}" \
    "$HOST/$api_update")

message=$(echo "$result" | jq .result | tr -d \")

if [ "$message" != "OK" ]; then
    echo "error: $result"
    exit 1
else
    echo "success: $result"
fi

#############################################################
# test 4:

api_delete="api/library?song_id=${SONG_ID}&root=${FS_ROOT}"

result=$(curl $VERBOSE -u "$AUTH" -X DELETE "$HOST/$api_delete")
if [ "$message" != "OK" ]; then
    echo "error: $result"
    exit 1
else
    echo "success: $result"
fi

#############################################################
# test 5:
api_query="api/fs/$FS_ROOT/path/$FS_PATH?list=true"

result=$(curl $VERBOSE -u "$AUTH" "$HOST/$api_query")
echo "$result"

#############################################################
# test 5:
api_query="api/library/$SONG_ID"

result=$(curl $VERBOSE -u "$AUTH" "$HOST/$api_query")
echo "$result"

#############################################################
# test 6:

api_delete="api/library?song_id=${SONG_ID}&root=${FS_ROOT}"

result=$(curl $VERBOSE -u "$AUTH" -X DELETE "$HOST/$api_delete")
echo "$result"

#29b49b86-f807-4ea5-81b2-bc4c91641a1d

#curl -u "admin:yue@AkaSakura1!" -X DELETE "https://yueapp.duckdns.org/api/library?song_id=29b49b86-f807-4ea5-81b2-bc4c91641a1d&root=music"
#! cd ../.. && python -m server.tools.upload --username admin --password admin beast.json test

import os
import sys
import argparse
import json
import hashlib
import io
import logging

from server.app import connect
from server.dao.transcode import FFmpeg

def truncated_hash(s, n):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]

def _list_dir(dircache, client, root, dir_path):
    if dir_path not in dircache:
        response = client.files_get_path(root, dir_path)
        if response.status_code != 404:
            data = response.json()['result']
            if data['files']:
                dircache[dir_path] = [o['name'] for o in data['files']]
    return dircache.get(dir_path, [])

def _transcode_upload(transcoder, client, local_path, root, remote_path, opts):
    if not local_path.endswith("ogg"):
        print("transcoding")

        # transcode the file into memory
        f = io.BytesIO()
        with open(local_path, "rb") as rb:
            transcoder.transcode_ogg(rb, f, **opts)

        f.seek(0)
        response = client.files_upload(root, remote_path, f.getvalue())
        if response.status_code != 200:
            print("failed: %s" % mp3_path)
        f.close()
    else:
        with open(local_path, "rb") as rb:
            response = client.files_upload(root, remote_path, rb)
            if response.status_code != 200:
                print("failed: %s" % mp3_path)

def _create_song(client, song):

    remote_song = dict(song)
    if 'file_path' in remote_song:
        del remote_song['file_path']
    if 'art_path' in remote_song:
        del remote_song['art_path']
    response = client.library_create_song(json.dumps(remote_song))
    if response.status_code != 201:
        print(response)
        print(response.status_code)
    song_id = response.json()['result']
    return song_id

def _update_song(client, song):

    remote_song = dict(song)
    if 'file_path' in remote_song:
        del remote_song['file_path']
    if 'art_path' in remote_song:
        del remote_song['art_path']

    response = client.library_update_song(json.dumps(remote_song))
    if response.status_code != 200:
        print(response)
        print(response.status_code)

def upload_one(client, transcoder, dircache, song, root):

    artist = truncated_hash(song['artist'], 32)
    album = truncated_hash(song['album'], 16)
    title = truncated_hash(song['title'], 16)

    _c = ord(song['artist'][0].upper())
    prefix = artist[:2]
    if ord('A') <= _c <= ord('Z'):
        prefix = song['artist'][0].upper()
    elif ord('0') <= _c <= ord('9'):
        prefix = song['artist'][0]

    name = title + "_%s" % song['ref_id']

    dir_path = "music/%s/%s/%s" % (prefix, artist, album)
    mp3_name = "%s.ogg" % (name)
    mp3_path = "%s/%s" % (dir_path, mp3_name)
    art_name = "%s.jpg" % (name)
    art_path = "%s/%s" % (dir_path, art_name)

    print(mp3_path)

    #--------------------------------------------------------------------------
    # list the directory to determine what files exist

    opts = {
        "nchannels": 2,
        "volume": 1.0,
        "samplerate": 44100,
        "bitrate": 256,
        "metadata": {
            "artist": song.get('artist', "Unknown Artist"),
            "title": song.get('title', "Unknown Title"),
            "album": song.get('album', "Unknown Album"),
        }
    }

    response = client.library_get_song_by_reference(str(song['ref_id']))
    if response.status_code == 200:
        print("found a song with reference: %s" % song['ref_id'])
        # remote_song = response.json()
        # print(remote_song)
        _update_song(client, song)

    else:
        print("creating song with reference: %s" % song['ref_id'])

        items = _list_dir(dircache, client, root, dir_path)

        if mp3_name not in items:
            _transcode_upload(transcoder, client,
                song['file_path'], root, mp3_path, opts)

        song_id = _create_song(client, song)

        payload = {
            "root": root,
            "path": mp3_path,
        }
        response = client.library_set_song_audio(song_id, json.dumps(payload))
        if response.status_code != 200:
            print(response)
            print(response.status_code)

def upload(client, songs, root):

    # music
    # first letter of name, uppercase, or "other"
    # hash the refid
    # file extension

    transcoder = FFmpeg("C:\\ffmpeg\\bin\\ffmpeg.exe")

    dircache = {}

    for song in songs:
        upload_one(client, transcoder, dircache, song, root)

def _read_json(path):

    if path == "-":
        return json.load(sys.stdin)
    elif path is not None:
        if not os.path.exists(path):
            sys.stdout.write("cannot find: %s" % path)
            sys.exit(1)
        return json.load(open(path))
    return None

def parseArgs(argv):

    parser = argparse.ArgumentParser(description='Sync tool')

    parser.add_argument('--username', default=None,
                    help='username')

    parser.add_argument('--password', default=None,
                    help='password')

    parser.add_argument('--host', dest='host',
                    default="http://localhost:4200",
                    help='the database connection string')

    parser.add_argument('file',
                    help='json file containing songs to upload')

    parser.add_argument('root',
                    help='media root to upload file to')

    args = parser.parse_args()

    return args

def main():

    args = parseArgs(sys.argv)

    client = connect(args.host, args.username, args.password)

    data = _read_json(args.file)

    upload(client, data, args.root)


if __name__ == '__main__':
    main()
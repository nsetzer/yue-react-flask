#! cd ../.. && python -m server.tools.upload --username admin --password admin beast.json test

import os
import sys
import argparse
import json
import hashlib

from server.app import connect
from server.dao.transcode import FFmpeg
from server.dao.filesys import FileSystem

def truncated_hash(s, n):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]

def upload(client, songs, root):

    # music
    # first letter of name, uppercase, or "other"
    # hash the refid
    # file extension

    fs = FileSystem()
    transcoder = FFmpeg("C:\\ffmpeg\\bin\\ffmpeg.exe")

    _a = ord('A')
    _z = ord('Z')

    dircache = {}

    print(client._endpoints.keys())

    for song in songs:
        artist = song['artist']
        _c = ord(artist[0].upper())

        c = "other"
        if _a <= _c <= _z:
            c = artist[0].upper()

        artist = truncated_hash(song['artist'], 16)
        name = truncated_hash(str(song['ref_id']), 32) + "_%s" % song['ref_id']

        dir_path = "music/%s/%s" % (c, artist)
        mp3_name = "%s.ogg" % (name)
        mp3_path = "music/%s/%s/%s.ogg" % (c, artist, name)
        art_name = "%s.jpg" % (name)
        art_path = "music/%s/%s/%s.jpg" % (c, artist, name)

        if dir_path not in dircache:
            response = client.files_get_path(root, dir_path)
            if response.status_code != 404:
                data = response.json()['result']
                if data['files']:
                    dircache[dir_path] = [o['name'] for o in data['files']]

        items = dircache.get(dir_path, [])

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

        if mp3_name not in items:

            if not song['file_path'].lower().endswith("mp3"):
                print("transcoding")

                with fs.open(song['file_path'], "rb") as rb:
                    with fs.open("mem://upload", "wb") as wb:
                        transcoder.transcode_ogg(rb, wb, **opts)

                with fs.open("mem://upload", "rb") as rb:
                    response = client.files_upload(root, mp3_path, rb.getvalue())
                    if response.status_code != 200:
                        print("failed: %s" % mp3_path)
            else:
                with open(song['file_path'], "rb") as rb:
                    response = client.files_upload(root, mp3_path, rb)
                    if response.status_code != 200:
                        print("failed: %s" % mp3_path)

        response = client.library_get_song_by_reference(str(song['ref_id']))
        if response.status_code == 200:
            print("found a song with reference: %s" % song['ref_id'])
            remote_song = response.json()
            print(remote_song)
        else:
            print("creating song with reference: %s" % song['ref_id'])
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
            payload = {
                "root": root,
                "path": mp3_path,
            }
            response = client.library_set_song_audio(song_id, json.dumps(payload))
            if response.status_code != 200:
                print(response)
                print(response.status_code)

        break

    # e.g. s3://bucket-name/music/A/0000.mp3
#
#    response = client.files_get_path(root, path)
#

#
#    payload = {
#        "root": root,
#        "path": "TODO",
#    }
#    set_song_audio(payload)
#

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
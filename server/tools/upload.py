#! cd ../.. && python -m server.tools.upload --host http://localhost:4200 --username admin --password admin mark.json test
#! cd ../.. && python -m server.tools.upload --host http://104.248.122.206:80 --username admin --password admin clutch.json temp

import os
import sys
import argparse
import json
import hashlib
import io
import logging
import posixpath

from server.app import connect
from server.dao.transcode import FFmpeg

class JsonUploader(object):
    """upload songs and art to a remote server
    update the datebase

    required song keys:
        static_path: the path on the remote server to upload to
        file_path: a path on the local file system pointing to a song file
        ref_id: a unique reference id for the song
        artist, title, album: describe this song

    optional song keys:
        art_path : a path on the local file system pointing to album artwork

    all other song keys can be provided.

    """
    def __init__(self, client, transcoder):
        super(JsonUploader, self).__init__()
        self.client = client
        self.transcoder = transcoder

    def upload(self, songs, root):
        self.dircache = {}
        for song in songs:
            self._upload_one(song, root)

    def _upload_one(self, song, root):

        file_path = song['file_path']
        static_path = song['static_path']
        ref_id = str(song['ref_id'])

        aud_path = "%s.ogg" % (static_path)
        _, aud_name = posixpath.split(aud_path)

        art_path = "%s.jpg" % (static_path)
        _, art_name = posixpath.split(art_path)


        # transcode options
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

        response = self.client.library_get_song_by_reference(ref_id)
        if response.status_code == 200:
            print("found a song with reference: %s" % ref_id)
            self._update_song(song)

        else:
            print("creating song with reference: %s" % ref_id)

            items = self._list_dir(root, static_path)

            if aud_name not in items:
                self._transcode_upload(file_path, root, aud_path, opts)

            song_id = self._create_song(song)

            payload = {
                "root": root,
                "path": aud_path,
            }
            response = self.client.library_set_song_audio(song_id,
                json.dumps(payload))
            if response.status_code != 200:
                print(response)
                print(response.status_code)

    def _list_dir(self, root, dir_path):
        if dir_path not in self.dircache:
            response = self.client.files_get_path(root, dir_path)
            if response.status_code != 404:
                data = response.json()['result']
                if data['files']:
                    self.dircache[dir_path] = [o['name'] for o in data['files']]
        return self.dircache.get(dir_path, [])

    def _transcode_upload(self, local_path, root, remote_path, opts):
        if not local_path.endswith("ogg"):
            print("transcoding")

            # transcode the file into memory
            f = io.BytesIO()
            with open(local_path, "rb") as rb:
                self.transcoder.transcode_ogg(rb, f, **opts)
            print("uploading")

            f.seek(0)
            response = self.client.files_upload(root, remote_path, f.getvalue())
            if response.status_code != 200:
                print(response.text)
                print(response.status_code)
                print("failed upload 1: %s" % remote_path)
                sys.exit(1)
            f.close()
        else:
            with open(local_path, "rb") as rb:
                response = self.client.files_upload(root, remote_path, rb)
                if response.status_code != 200:
                    print(response.status_code)
                    print("failed uplaod 2: %s" % remote_path)

    def _prepare_song_for_transport(self, song):

        remote_song = dict(song)
        if 'static_path' in remote_song:
            del remote_song['static_path']
        if 'file_path' in remote_song:
            del remote_song['file_path']
        if 'art_path' in remote_song:
            del remote_song['art_path']

        return remote_song

    def _create_song(self, song):

        remote_song = self._prepare_song_for_transport(song)

        response = self.client.library_create_song(json.dumps(remote_song))
        if response.status_code != 201:
            print(response)
            print(response.status_code)
        song_id = response.json()['result']
        return song_id

    def _update_song(self, song):

        remote_song = self._prepare_song_for_transport(song)

        response = self.client.library_update_song(json.dumps(remote_song))
        if response.status_code != 200:
            print(response)
            print(response.status_code)

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

    if args.password is None:
        args.password = input("password:")

    return args

def main():

    args = parseArgs(sys.argv)

    client = connect(args.host, args.username, args.password)

    data = _read_json(args.file)

    transcoder = FFmpeg("C:\\ffmpeg\\bin\\ffmpeg.exe")

    JsonUploader(client, transcoder).upload(data, args.root)


if __name__ == '__main__':
    main()
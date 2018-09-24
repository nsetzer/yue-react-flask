#! cd ../.. && python -m yueserver.tools.upload --host http://localhost:4200 -n 4 --username admin --password admin mark.json default
#! cd ../.. && python -m yueserver.tools.upload --host https://yueapp.duckdns.org:443 --username admin -n 4 mark.json music

"""
Upload songs to a remote server and update the database

sample of what a song record should be formatted as:
see server.dao.library for the complete documentation
on keys that are available for songs


    song = {
        "ref_id": 1234
        "static_path": "artist/album/title"
        "file_path" : "/mnt/music/artist/album/title.mp3"
        "art_path" : "/mnt/music/artist/album/folder.jpg"
        "artist": "artistname"
        "album": "albumname"
        "title": "title"
    }

"""
import os
import sys
import argparse
import json
import hashlib
import io
import logging
import posixpath

from ..app import connect
from ..dao.transcode import FFmpeg
from ..dao.filesys.s3fs import BotoFileSystemImpl

from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count

try:
    import boto3
    import botocore
except ImportError:
    boto3 = None
    botocore = None

class S3Upload(object):
    """docstring for S3Upload"""
    def __init__(self, bucket):
        super(S3Upload, self).__init__()
        self.bucket = bucket

        access_key = os.environ['AWS_ACCESS_KEY_ID']
        secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
        endpoint = os.environ['AWS_ENDPOINT_URL']
        region = os.environ['AWS_DEFAULT_REGION']

        self.fs = BotoFileSystemImpl(endpoint, region, access_key, secret_key)

    def upload(self, remote_path, fo):
        path = posixpath.join(self.bucket, remote_path)
        print("[s3] uploading to %s" % path)
        with self.fs.open(path, "wb") as wf:
            for buf in iter(lambda: fo.read(4096), b""):
                wf.write(buf)

class JsonUploader(object):
    """upload songs and art to a remote server
    update the datebase

    required song keys:
        static_path: the path on the remote server to upload to
        file_path: a path on the local file system pointing to a song file
        artist, title, album: describe this song

    optional song keys:
        art_path : a path on the local file system pointing to album artwork

    all other song keys can be provided.

    Note: the static_path is used to determine if a local song exists on
    the remote server. It should be a relative path, with a filename but
    without an extension. e.g. "artist/album/title". It should be
    unique across all songs (across all domains)

    """
    def __init__(self, client, transcoder, root, bucket):
        super(JsonUploader, self).__init__()
        self.client = client
        self.transcoder = transcoder
        self.root = root

        if bucket is not None:
            self.s3fs = S3Upload(bucket)
        else:
            self.s3fs = None

    def upload(self, songs, remote_songs, remote_files):
        for song in songs:
            self._upload_one(song, remote_songs, remote_files)

    def _upload_one(self, song, remote_songs, remote_files):

        file_path = song['file_path']
        static_path = song['static_path']

        dir_path, _ = posixpath.split(static_path)

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

        if static_path in remote_songs:
            logging.info("update: %s" % static_path)
            song['id'] = remote_songs[static_path]['id']
            self._update_song(song)
        else:
            logging.info("create: %s" % static_path)

            if aud_name not in remote_files:
                self._transcode_upload(file_path, aud_path, opts)

            song_id = self._create_song(song)

            payload = {
                "root": self.root,
                "path": aud_path,
            }
            response = self.client.library_set_song_audio(song_id,
                json.dumps(payload))
            if response.status_code != 200:
                print(response)
                print(response.status_code)

    def _transcode_upload(self, local_path, remote_path, opts):
        if not local_path.endswith("ogg"):
            # transcode the file into memory
            f = io.BytesIO()

            try:
                with open(local_path, "rb") as rb:
                    self.transcoder.transcode_ogg(rb, f, **opts)

                f.seek(0)
                if self.s3fs is not None:
                    self.s3fs.upload(remote_path, f)
                else:
                    self._api_upload(remote_path, f)
            finally:
                f.close()

        else:
            with open(local_path, "rb") as rb:
                if self.s3fs is not None:
                    self.s3fs.upload(remote_path, rb)
                else:
                    self._api_upload(remote_path, rb)

    def _api_upload(self, remote_path, fo):
        response = self.client.files_upload(self.root, remote_path, fo)
        if response.status_code != 200:
            print(response.text)
            print(response.status_code)
            print("failed upload 1: %s" % remote_path)
            sys.exit(1)

    def _prepare_song_for_transport(self, song):

        remote_song = dict(song)
        #if 'static_path' in remote_song:
        #    del remote_song['static_path']
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
            print(remote_song)
            print(response.text)

        song_id = response.json()['result']
        return song_id

    def _update_song(self, song):

        remote_song = self._prepare_song_for_transport(song)

        response = self.client.library_update_song(json.dumps([remote_song]))
        if response.status_code != 200:
            print(response)
            print(response.status_code)
            print(remote_song)
            print(response.text)

def _read_json(path):

    if path == "-":
        return json.load(sys.stdin)
    elif path is not None:
        if not os.path.exists(path):
            sys.stdout.write("cannot find: %s" % path)
            sys.exit(1)
        return json.load(open(path))
    return None

def _fetch_files(client, root):

    files = set()

    page = 0
    limit = 500
    while True:
        logging.info("fetch files page:%d" % page)
        params = {'limit': limit, 'page': page}
        response = client.files_get_index_root(root, **params)
        if response.status_code != 200:
            sys.stderr.write("fetch songs error...\n")
            sys.exit(1)

        result = response.json()['result']
        for f in result:
            files.add(f['path'])

        page += 1
        if len(result) != limit:
            break

    logging.info("fetched %d files" % len(files))
    return files

def _fetch_songs(client):

    songs = dict()

    page = 0
    limit = 500
    while True:
        logging.info("fetch songs page:%d" % page)
        params = {'limit': limit, 'page': page}
        response = client.library_search_library(**params)
        if response.status_code != 200:
            sys.stderr.write(response.text)
            sys.stderr.write("fetch songs error...\n")
            sys.exit(1)

        result = response.json()['result']
        for s in result:
            songs[s['static_path']] = s

        page += 1
        if len(result) != limit:
            break

    logging.info("fetched %d songs" % len(songs))
    return songs

def do_upload(client, data, root, nparallel=1, bucket=None, ffmpeg_path=None):

    transcoder = FFmpeg(ffmpeg_path)

    rsongs = _fetch_songs(client)
    rfiles = _fetch_files(client, root)

    if nparallel == 1:
        uploader = JsonUploader(client, transcoder, root, bucket)
        uploader.upload(data, rsongs, rfiles)

    else:
        # partition the data into n groups,
        # use the futures library to upload files in parallel
        uploaders = []
        partition = [[] for i in range(nparallel)]
        futures = []

        for i in range(nparallel):
            uploaders.append(JsonUploader(client, transcoder,
                root, bucket))

        for i, item in enumerate(data):
            partition[i % len(partition)].append(item)

        with ThreadPoolExecutor(max_workers=nparallel) as executor:

            for i in range(nparallel):
                future = executor.submit(
                    uploaders[i].upload, partition[i], rsongs, rfiles)
                futures.append(future)

def parseArgs(argv):

    parser = argparse.ArgumentParser(
        description='upload songs to a remote server')

    parser.add_argument('--username', default=None,
                    help='username')

    parser.add_argument('--password', default=None,
                    help='password')

    parser.add_argument('--host',
                    default="http://localhost:4200",
                    help='the database connection string')

    parser.add_argument('--ffmpeg',
                    default="C:\\ffmpeg\\bin\\ffmpeg.exe",
                    help='the path to the ffmpeg binary')

    parser.add_argument('--bucket', default=None,
                    help='an s3 bucket name and path, e.g. s3://bucket/path')

    parser.add_argument('-n', '--nparallel', type=int, default=1,
                    help='the database connection string')

    parser.add_argument('file',
                    help='json file containing songs to upload')

    parser.add_argument('root',
                    help='media root to upload file to')

    args = parser.parse_args()

    if args.password is None:
        args.password = input("password:")

    if args.nparallel > cpu_count():
        raise Exception("nparallel: %d cpu_count:%d" % (
            args.nparallel, cpu_count()))

    return args

def main():

    logging.basicConfig(level=logging.INFO)
    args = parseArgs(sys.argv)

    client = connect(args.host, args.username, args.password)

    data = _read_json(args.file)

    do_upload(client, data, args.root,
        args.nparallel, args.bucket, args.ffmpeg)

if __name__ == '__main__':
    main()
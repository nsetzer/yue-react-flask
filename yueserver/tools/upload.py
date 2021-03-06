#! cd ../.. && python -m yueserver.tools.upload --host http://localhost:4200 -n 4 --username admin --password admin mark.json default
#! cd ../.. && python -m yueserver.tools.upload --host https://yueapp.duckdns.org:443 --username admin -n 4 mark.json music

"""
Upload songs to a remote server and update the database

sample of what a song record should be formatted as:
see server.dao.library for the complete documentation
on keys that are available for songs


    song = {
        "ref_id": 1234,
        "static_path": "artist/album/title",
        "file_path": "/mnt/music/artist/album/title.mp3",
        "art_path": "/mnt/music/artist/album/folder.jpg",
        "artist": "artistname",
        "album": "albumname",
        "title": "title",
        "equalizer": 0,
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
import time

from ..app import connect
from ..dao.transcode import FFmpeg
from ..dao.filesys.s3fs import BotoFileSystemImpl

from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count

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
    def __init__(self, client, transcoder, root, bucket, noexec, create, update):
        super(JsonUploader, self).__init__()
        self.client = client
        self.transcoder = transcoder
        self.root = root
        self.noexec = noexec

        self.do_update = update
        self.do_create = create
        print("create: %s update: %s" % (create, update))

        self.update_keys = ['artist', 'artist_key', 'composer',
                            'album', 'title', 'genre', 'year',
                            'country', 'language', 'comment', 'rating']

        if bucket is not None:
            self.s3fs = S3Upload(bucket)
            self._upload_impl = self.s3fs.upload
        else:
            self.s3fs = None
            self._upload_impl = self._api_upload

    def upload(self, songs, remote_songs, remote_files):
        self.updated = 0
        self.uploaded = 0
        count = 0
        start = time.time()
        for local_song in songs:
            count += 1

            static_path = local_song['static_path']
            remote_song = None
            if static_path in remote_songs:
                remote_song = remote_songs[static_path]

            try:
                self._upload_one(local_song, remote_song, remote_files)
            except Exception as e:
                logging.exception("upload %s" % e)
        end = time.time()
        success = self.updated + self.uploaded
        logging.warning("%d/%d (uploaded: %d updated: %d) in %s seconds" % (
            success, count, self.uploaded, self.updated, end - start))
        logging.warning("remote_songs: %d" % len(remote_songs))
        logging.warning("remote_files: %d" % len(remote_files))

    def _upload_one(self, local_song, remote_song, remote_files):

        file_path = local_song['file_path']
        static_path = local_song['static_path']

        dir_path, _ = posixpath.split(static_path)

        aud_path = "%s.ogg" % (static_path)
        _, aud_name = posixpath.split(aud_path)

        art_path = "%s.jpg" % (static_path)
        _, art_name = posixpath.split(art_path)

        # transcode options
        volume = min(2.0, local_song['equalizer'] / 100.0)
        if volume < 0.2:
            volume = 1.0

        opts = {
            "volume": volume,
            "samplerate": 44100,
            "scale": 4,
            "metadata": {
                "ARTIST": local_song.get('artist', "Unknown Artist"),
                "ALBUM": local_song.get('album', "Unknown Title"),
                "TITLE": local_song.get('title', "Unknown Album"),
            }
        }

        # volume has been normalized, so set equalizer to default
        local_song['equalizer'] = 100

        _update = (remote_song is not None)
        if not self.do_update:
            _update = _update and (aud_path in remote_files)

        if _update:

            if not self.do_update:
                print("skip", aud_path)
                return

            # find keys that are different
            track = {}
            for key in self.update_keys:
                if local_song[key] != remote_song[key]:
                    track[key] = local_song[key]

            if not track:
                logging.info("up to date: %s %d" % (static_path, len(track)))
                return;
            else:

                logging.info("update    : %s %d" % (static_path, len(track)))

            self.updated += 1

            if self.noexec:
                return

            update_song = dict(local_song)

            #for key in ['artist', 'artist_key', 'album', 'title',
            #            'composer', 'genre', 'year', 'comment', 'country', 'language',
            #            'banished']:
            #   update_song[key] = remote_song[key]

            update_song['id'] = remote_song['id']

            self._update_song(update_song)
        else:
            if not self.do_create:
                logging.info("skip create")
                return

            # never create if already exists
            if remote_song is not None:
                # the only reason to hit this line would be to reupload audio
                # which isnt implemented -- delete and recreate instead
                logging.info("skip create")
                return

            if aud_path in remote_files:
                logging.info("create: %s" % aud_path)
            else:
                logging.info("upload: %s" % aud_path)

            self.uploaded += 1

            if self.noexec:
                return

            if aud_path not in remote_files:
                self._transcode_upload(file_path, aud_path, opts)

            song_id = self._create_song(local_song)

            if song_id:
                self._set_audio_path(song_id, aud_path)

    def _transcode_upload(self, local_path, remote_path, opts):
        if not local_path.endswith("ogg"):
            logging.info("transcoding file")
            # transcode the file into memory
            f = io.BytesIO()

            try:
                with open(local_path, "rb") as rb:
                    cmd = self.transcoder.get_ogg_args(**opts)
                    self.transcoder.transcode(rb, f, cmd)

                logging.info("uploading file")

                f.seek(0)
                self._upload_impl(remote_path, f)
            finally:
                f.close()

        else:
            logging.info("uploading file")
            with open(local_path, "rb") as rb:
                self._upload_impl(remote_path, rb)

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
            print("remote", remote_song)
            print("response text", response.status_code, response.text)
            return None


        result = json.loads(response.text)
        song_id = result['result']

        #song_id = response.json()['result']
        return song_id

    def _update_song(self, song):

        remote_song = self._prepare_song_for_transport(song)

        response = self.client.library_update_song(json.dumps([remote_song]))
        if response.status_code != 200:
            print(response)
            print(response.status_code)
            print(remote_song)
            print(response.text)

    def _set_audio_path(self, song_id, aud_path):
        payload = {
            "root": self.root,
            "path": aud_path,
        }
        print("set audio path", song_id, payload)
        response = self.client.library_set_song_audio(song_id,
            json.dumps(payload))
        if response.status_code != 200:
            raise Exception("[%s] unable to st audio" % response.status_code)

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
    limit = 2000
    while True:
        logging.info("fetch files page:%d" % page)
        params = {'limit': limit, 'page': page}
        response = client.files_get_index_root(root, **params)
        if response.status_code != 200:
            sys.stderr.write("%s\n" % response.text)
            sys.stderr.write("fetch songs error...\n")
            sys.exit(1)

        result = response.json()
        print(result)
        result = result['result']
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
    limit = 2000
    while True:

        params = {
            'limit': limit,
            'page': page,
            'orderby': 'id',
            'showBanished': True
        }
        response = client.library_search_library(**params)
        if response.status_code != 200:
            sys.stderr.write("%s\n" % response.text)
            sys.stderr.write("fetch songs error...\n")
            sys.exit(1)

        result = response.json()['result']
        for s in result:
            if s['static_path'] in songs:
                print(songs[s['static_path']])
                print(s)
                raise Exception(s['static_path'])
            songs[s['static_path']] = s

        logging.info("fetch songs page:%d ...  %d" % (page, len(result)))

        page += 1
        if len(result) != limit:
            break

    logging.info("fetched %d songs" % len(songs))

    #curl -u admin:admin "http://localhost:4200/api/fs/default/index"

    return songs

def do_upload(client, data, root, nparallel=1, bucket=None, ffmpeg_path=None, noexec=False, create=True, update=False):

    transcoder = FFmpeg(ffmpeg_path)

    rsongs = _fetch_songs(client)
    print(client, root)
    rfiles = _fetch_files(client, root)

    # TODO: a keyboard interrupt should wait for the current task to complete

    if nparallel == 1:
        uploader = JsonUploader(client, transcoder,
            root, bucket, noexec, create, update)
        uploader.upload(data, rsongs, rfiles)

    else:
        # partition the data into n groups,
        # use the futures library to upload files in parallel
        uploaders = []
        partition = [[] for i in range(nparallel)]
        futures = []

        for i in range(nparallel):
            uploaders.append(JsonUploader(client, transcoder,
                root, bucket, noexec, create, update))

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



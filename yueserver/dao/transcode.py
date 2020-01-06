
"""
An FFmpeg transcode class

convert any audio format into an mp3
"""
import os
import sys
import io
import subprocess
import threading
import logging
from threading import Thread

from .image import scale_image_stream, ImageScale

from .filesys.util import sh_escape

def find_ffmpeg():
    ffmpeg_paths = [
        '/bin/ffmpeg',
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        'C:\\ffmpeg\\bin\\ffmpeg.exe'
    ]

    for path in ffmpeg_paths:
        if os.path.exists(path):
            return path
    return None

# duplicate functions so that errors in the logs
# will reflect which side of the channel failed
def _pushsrc(src, dst):
    buf = src.read(2048)
    while buf:
        dst.write(buf)
        buf = src.read(2048)

def _pushdst(src, dst):
    buf = src.read(2048)
    while buf:
        dst.write(buf)
        buf = src.read(2048)

def async_transcode(cmd, src, dst, ignore=False):

        logging.debug(' '.join(cmd))

        proc = subprocess.Popen(cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # stderr=subprocess.DEVNULL,
            shell=False)

        f1 = threading.Thread(target=_pushsrc, args=(src, proc.stdin))
        f2 = threading.Thread(target=_pushdst, args=(proc.stdout, dst))

        f1.start()
        f2.start()

        f1.join()
        try:
            proc.stdin.close()
        except BrokenPipeError as e:
            # ignore broken pipes when extracting keyframes
            if not ignore:
                logging.exception("ok")
                raise

        f2.join()
        proc.stdout.close()

        proc.wait()

class _TranscodeFileThread(Thread):
    """ A thread for copying bytes from an input file into and output file
        useful for feeding input into the ffmpeg process from
        a file-stream which exists in memory
    """
    def __init__(self, infile, outfile):
        super(_TranscodeFileThread, self).__init__()
        self.infile = infile
        self.outfile = outfile

    def run(self):

        try:
            for buf in iter(lambda: self.infile.read(2048), b""):
                self.outfile.write(buf)
        finally:
            self.outfile.close()

class _TranscodeFile(object):
    """A file-like for transcoding in-memory

    does not support seeking
    """
    def __init__(self, cmd, infile):
        super(_TranscodeFile, self).__init__()

        logging.debug("execute: %s" % sh_escape(cmd))

        self._proc = subprocess.Popen(cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL)

        self._thread = _TranscodeFileThread(infile, self._proc.stdin)
        self._thread.start()

        self.read = self._proc.stdout.read

        self.returncode = -1

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def close(self):

        self._thread.join()
        self._proc.stdout.close()
        self._proc.wait()
        self.returncode = self._proc.returncode

class FFmpeg(object):
    """docstring for FFmpeg"""
    def __init__(self, binpath):
        super(FFmpeg, self).__init__()
        self.binpath = binpath

    def get_mp3_args(self, **kwargs):

        args = [self.binpath, "-i", "pipe:0"]

        args.append("-acodec")
        args.append("mp3")

        if 'bitrate' in kwargs:
            args.append("-ab")
            args.append("%dk" % kwargs['bitrate'])

        if 'samplerate' in kwargs:
            args.append("-ar")
            args.append("%s" % kwargs['samplerate'])

        if 'nchannels' in kwargs:
            args.append("-ac")
            args.append("%s" % kwargs['nchannels'])

        args.append("-vn")

        if 'volume' in kwargs:
            args.append("-vol")
            vol = int(max(0.2, min(2.0, kwargs['volume'])) * 256)
            args.append("%s" % vol)

        if 'metadata' in kwargs:
            for key, value in kwargs['metadata'].items():
                args.append("-metadata")
                args.append("%s=%s" % (key, value))

        args.append("-write_xing")
        args.append("0")

        args.append("-id3v2_version")
        args.append("3")

        args.append("-write_id3v1")
        args.append("1")

        args.append("-f")
        args.append("mp3")
        args.append("pipe:1")

        return args

    def get_ogg_args(self, **kwargs):
        """
            kwargs:
                scale: integer in range 0-10
                volume: float in range 0.2 to 2.0, 1.0 is default
                        2.0 will double the volume and may cause clipping
                nchannels:
                samplerate
                metadata: {"ARTIST": "artist",
                           "ALBUM": "album",
                           "TITLE": "title", } etc
        """

        if self.binpath is None:
            raise Exception("transcoder binpath is none")
        args = [self.binpath, "-i", "pipe:0"]

        args.append("-c:a")
        args.append("libvorbis")

        #args.append("-b:a")
        #args.append("256k")

        args.append("-qscale:a")
        args.append(str(kwargs.get("scale", 3)))

        # no video output
        args.append("-vn")

        if 'volume' in kwargs:
            args.append("-vol")
            vol = int(max(0.2, min(2.0, kwargs['volume'])) * 256)
            args.append("%s" % vol)

        # strip existing metadata
        args.append("-map_metadata:g")
        args.append("-1:g")

        if 'metadata' in kwargs:
            for key, value in kwargs['metadata'].items():
                args.append("-metadata")
                args.append("%s=%s" % (key, value))

        if 'nchannels' in kwargs:
            args.append("-ac")
            args.append("%s" % kwargs['nchannels'])

        if 'samplerate' in kwargs:
            args.append("-ar")
            args.append("%s" % kwargs['samplerate'])

        args.append("-f")
        args.append("ogg")
        args.append("pipe:1")

        return args

    def get_thumb_args(self, **kwargs):

        args = [self.binpath, "-i", "pipe:0"]

        # extract a key frame from 5 seconds into the video
        args.append('-ss')
        args.append('00:00:05.000')

        # extract one key frame
        args.append("-vframes")
        args.append("1")

        args.append("-f")
        args.append("mjpeg")

        # write output
        args.append("pipe:1")

        return args

    def transcode(self, infile, outfile, args):
        async_transcode(args, infile, outfile)

    def thumb(self, infile, outfile, args, scale):
        with io.BytesIO() as tmpfile:
            async_transcode(args, infile, tmpfile, True)
            if tmpfile.tell() == 0:
                raise Exception("failed to transcode file")
            return scale_image_stream(tmpfile, outfile, scale)


def main():

    logging.basicConfig(level=logging.DEBUG)
    binpath = find_ffmpeg()

    transcoder = FFmpeg(binpath)

    if len(sys.argv) != 4:
        print("usage:")
        print("   %s [transcode|thumb] src dst" % sys.argv[0])
        sys.exit(1)

    if sys.argv[1] == 'transcode':

        args = transcoder.get_ogg_args()
        with open(sys.argv[2], 'rb') as src:
            with open(sys.argv[3], 'wb') as dst:
                transcoder.transcode(args, src, dst)

    elif sys.argv[1] == 'thumb':

        args = transcoder.get_thumb_args()
        with open(sys.argv[2], 'rb') as src:
            with open(sys.argv[3], 'wb') as dst:
                transcoder.thumb(src, dst, args, ImageScale.THUMB)

    else:
        print("unrecognized mode: %s" % sys.argv[1])
        sys.exit(1)

if __name__ == '__main__':
    main()

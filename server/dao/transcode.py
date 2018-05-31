
import os, sys
import subprocess
import threading
import logging

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

def _push(src, dst):
    buf = src.read(2048)
    while buf:
        dst.write(buf)
        buf = src.read(2048)

def async_transcode(cmd, src, dst):

        logging.info(' '.join(cmd))

        proc = subprocess.Popen(cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False)

        f1 = threading.Thread(target=_push, args=(src, proc.stdin))
        f2 = threading.Thread(target=_push, args=(proc.stdout, dst))

        f1.start()
        f2.start()

        f1.join()
        proc.stdin.close()

        f2.join()
        proc.stdout.close()

        proc.wait()

class FFmpeg(object):
    """docstring for FFmpeg"""
    def __init__(self, binpath):
        super(FFmpeg, self).__init__()
        self.binpath = binpath

    def transcode(self, infile, outfile, **kwargs):

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

        if 'volume' in kwargs:
            args.append("-vol")
            vol = int(max(0.2, min(2.0, kwargs['volume'])) * 256)
            args.append("%s" % vol)

        if 'metadata' in kwargs:
            for key, value in kwargs['metadata'].items():
                args.append("-metadata")
                args.append("%s=%s" % (key, value))

        args.append("-f")
        args.append("mp3")
        args.append("pipe:1")

        async_transcode(args, infile, outfile)


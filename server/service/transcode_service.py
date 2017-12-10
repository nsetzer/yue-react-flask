
import os, sys
from ..dao.library import Song
from .util import TranscodeServiceException, FFmpegEncoder

class TranscodeService(object):
    """docstring for UserService"""

    _instance = None

    def __init__(self, db, dbtables):
        super(TranscodeService, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.encoder = FFmpegEncoder("/usr/bin/ffmpeg")

    @staticmethod
    def init(db, dbtables):
        if not TranscodeService._instance:
            TranscodeService._instance = TranscodeService(db, dbtables)
        return TranscodeService._instance

    @staticmethod
    def instance():
        return TranscodeService._instance

    def shouldTranscodeSong(self, song):
        srcpath = song[Song.path]
        print(srcpath)
        return not srcpath.lower().endswith('mp3')

    def transcodeSong(self, song):
        srcpath = song[Song.path]
        tgtpath = "/tmp/yue-audio"

        if not os.path.exists(tgtpath):
            os.makedirs(tgtpath)

        tgtpath = os.path.join(tgtpath, song[Song.id] + ".mp3")

        metadata=dict(
            artist=song[Song.artist],
            album=song[Song.album],
            title=song[Song.title]
        )

        #if Song.eqfactor > 0:
        #    vol = song[Song.equalizer] / Song.eqfactor
        #else:
        #    vol = 1.0
        vol = 1.0

        bitrate = 320
        if srcpath.lower().endswith('mp3'):
            bitrate=0

        if not os.path.exists(tgtpath):
            self.encoder.transcode(srcpath,tgtpath,bitrate,vol=vol,metadata=metadata)

        return tgtpath;
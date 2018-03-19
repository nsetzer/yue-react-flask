
import os, sys
from ..dao.library import Song
from .util import TranscodeServiceException, FFmpegEncoder
from ..config import Config

class TranscodeService(object):
    """docstring for UserService"""

    _instance = None

    def __init__(self, db, dbtables):
        super(TranscodeService, self).__init__()
        self.db = db
        self.dbtables = dbtables

        self.encoder = FFmpegEncoder(Config.instance().transcode.audio.bin_path)

    @staticmethod
    def init(db, dbtables):
        if not TranscodeService._instance:
            TranscodeService._instance = TranscodeService(db, dbtables)
        return TranscodeService._instance

    @staticmethod
    def instance():
        return TranscodeService._instance

    def shouldTranscodeSong(self, song, mode):

        if mode == "raw":
            return False;
        srcpath = song[Song.path]
        return not srcpath.lower().endswith('mp3')

    def transcodeSong(self, song, mode):

        srcpath = song[Song.path]
        tgtpath = Config.instance().transcode.audio.tmp_path

        if mode == "raw":
            return srcpath;

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
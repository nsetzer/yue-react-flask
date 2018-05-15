
import os, sys
from ..dao.library import Song
from .util import TranscodeServiceException, FFmpegEncoder

class TranscodeService(object):
    """docstring for TranscodeService"""

    _instance = None

    def __init__(self, config, db, dbtables):
        super(TranscodeService, self).__init__()
        self.config = config
        self.db = db
        self.dbtables = dbtables

        enc_path = config.transcode.audio.bin_path

        if enc_path and not os.path.exists(enc_path):
            raise FileNotFoundError(enc_path)

        self.encoder = FFmpegEncoder(enc_path)

    @staticmethod
    def init(config, db, dbtables):
        if not TranscodeService._instance:
            TranscodeService._instance = TranscodeService(config, db, dbtables)
        return TranscodeService._instance

    @staticmethod
    def instance():
        return TranscodeService._instance

    def shouldTranscodeSong(self, song, mode):
        """
        mode:
            default: transcode to mp3_320_2ch
            original: do not transcode

        todo: the env/app config should support specifing modes
            allow for: mono, stereo; 320, 256, 128; mp3, flac, etc;

        limit the available modes to a predefined list
        """

        if mode == "original":
            return False;

        srcpath = song[Song.path]
        return not srcpath.lower().endswith('mp3')

    def transcodeSong(self, song, mode):

        srcpath = song[Song.path]
        tgtpath = self.config.transcode.audio.tmp_path

        if mode == "original":
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
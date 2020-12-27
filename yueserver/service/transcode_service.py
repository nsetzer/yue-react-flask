
"""
The transcode service enables file format conversion of media.

Audio files can be converted using FFmpeg

Image files can be processed using the pillow library.
"""
import os, sys
from ..dao.library import Song
from ..dao.image import ImageScale, scale_image_file
from ..dao.filesys.filesys import FileSystem
from ..dao.transcode import FFmpeg, _TranscodeFile
from .exception import TranscodeServiceException
import logging
import io

class TranscodeService(object):
    """docstring for TranscodeService"""

    _instance = None

    def __init__(self, config, db, dbtables):
        super(TranscodeService, self).__init__()
        self.config = config
        self.db = db
        self.dbtables = dbtables

        self.fs = FileSystem()

        path = config.transcode.audio.bin_path

        if path and not os.path.exists(path):
            raise FileNotFoundError(path)

        self.transcoder = FFmpeg(path)

    @staticmethod
    def init(config, db, dbtables):
        if not TranscodeService._instance:
            TranscodeService._instance = TranscodeService(config, db, dbtables)
        return TranscodeService._instance

    @staticmethod
    def instance():
        return TranscodeService._instance

    def shouldTranscodeSong(self, song, format):

        if format == "default":
            format = config.transcode.audio.default_format

        srcpath = song[Song.path]
        ext = srcpath.lower()[-3:]

        if format == "raw" or ext == format:
            return False

        return True

    def _getTranscodeCommand(self, song, format, quality, nchannels, volume):

        if format == "default":
            format = config.transcode.audio.default_format

        srcpath = song[Song.path]
        ext = srcpath.lower()[-3:]

        opts = {}

        if nchannels > 0:
            opts["nchannels"] = nchannels

        if format == "raw" or ext == format:
            return None

        elif format == "ogg":
            ogg_quality = {
                "low": 2,
                "medium": 4,
                "high": 6,
            }
            opts['scale'] = ogg_quality[quality]
            method = self.transcoder.get_ogg_args

        elif format == "mp3":
            mp3_quality = {
                "low": 192,
                "medium": 256,
                "high": 320,  # browsers may not support
            }
            opts['bitrate'] = mp3_quality[quality]
            method = self.transcoder.get_mp3_args

        else:
            raise TranscodeServiceException("invalid format: %s" % format)

        opts['volume'] = volume

        opts['metadata'] = {
            "ARTIST": song.get(Song.artist, "Unknown Artist"),
            "ALBUM": song.get(Song.title, "Unknown Title"),
            "TITLE": song.get(Song.album, "Unknown Album"),
        }

        return method(**opts)

    def _transcodeSongGenImpl(self, path, cmd):
        with self.fs.open(path, "rb") as rb:
            with _TranscodeFile(cmd, rb) as tb:
                for buf in iter(lambda: tb.read(2048), b""):
                    yield buf

    def audioName(self, song, format, quality, nchannels=2):

        if format == "default":
            format = config.transcode.audio.default_format

        name = song[Song.id]

        if format == "raw":
            ext = self.fs.splitext(self.fs.split(song[Song.path])[1])[1]
            return "%s%s" % (name, ext)
        elif nchannels > 0:
            return "%s.%s.%s.%s" % (name, nchannels, quality, format)
        else:
            return "%s.%s.%s" % (name, quality, format)

    def transcodeSongGen(self, song, format, quality, nchannels=2, volume=1.0):

        cmd = self._getTranscodeCommand(song, format, quality, nchannels, volume)

        if cmd is not None:
            return self._transcodeSongGenImpl(song[Song.path], cmd)

        return None

    def transcodeSong(self, song, format, quality, nchannels=2, volume=1.0):
        """
        format: ogg, mp3, raw
            raw: return the file without transcoding
            mp3: transcode to mp3 if required
            ogg: transcode to ogg if required

        quality: low, medium, high
            raw: not applicable
            ogg: scale of 2,3 or 6 (on a 0 to 10 point scale)
            mp3: bitrate of 128K, 256K, or 320K

        nchannels: 1 or 2
            raw: not applicable
            ogg: output mono or stereo
            mp3: output mono or stereo

        """

        cmd = self._getTranscodeCommand(song, format, quality, nchannels, volume)

        if cmd is None:
            return song[Song.path]

        suffix = ".%s.%s.%s" % (nchannels, quality, format)
        tmppath = self.config.transcode.audio.tmp_path
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)
        tgtpath = os.path.join(tmppath, song[Song.id] + suffix)

        if not os.path.exists(tgtpath):
            with self.fs.open(song[Song.path], "rb") as rb:
                with self.fs.open(tgtpath, "wb") as wb:
                    self.transcoder.transcode(rb, wb, cmd)

        return tgtpath

    def scaleImage(self, src_path, tgt_path, scale):
        w, h, _ = scale_image_file(self.fs, src_path, tgt_path, scale)
        return w, h

    def getScaledAlbumArt(self, song, scale):
        """
        return the path to the album art for the given song

        the image identified by the path will have dimensions
        determined by the scale factor

        return None if there is no art for this image at the requested size.

        song: a song
        scale: an ImageScale enum
        """

        src_path = song[Song.art_path]

        if not src_path:
            # when displaying album art as part of a resource, instead
            # of returning the default path, return a 303 redirect
            # to the url of the default art.
            # TODO: this should be a 404 error
            logging.info("album art not found: `%s`" % src_path)
            raise TranscodeServiceException("file not found")

        dir, name  = self.fs.split(src_path)
        name, _ = self.fs.splitext(name)
        name = "%s.%s.png" % (name, ImageScale.name(scale))
        tgt_path = self.fs.join(dir, name)

        if not self.fs.exists(tgt_path):
            self.scaleImage(src_path, tgt_path, scale)

        return tgt_path

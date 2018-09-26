
"""
The transcode service enables file format conversion of media.

Audio files can be converted using FFmpeg

Image files can be processed using the pillow library.
"""
import os, sys
from ..dao.library import Song
from ..dao.filesys.filesys import FileSystem
from ..dao.transcode import FFmpeg, _TranscodeFile
from .exception import TranscodeServiceException
import logging
import io

from PIL import Image, ImageOps

class ImageScale(object):
    # square images
    # Large:  512px x 512px
    # Medium: 256px x 256px
    # small:  128px x 128px
    # 16x9 images
    # landscape: 512px x 288px
    # landscape_small: 256px x 144px

    SMALL  = 1
    MEDIUM = 2
    LARGE  = 3

    LANDSCAPE = 6
    LANDSCAPE_SMALL = 7

    _sizes = [
        (0, 0),
        (128, 128),
        (256, 256),
        (512, 512),
        (1024, 1024),
        (0, 0),
        (512, 288),
        (256, 144),
    ]

    _names = [
        "unknown",
        "small",
        "medium",
        "large",
        "unknown",
        "unknown",
        "landscape",
        "landscape_small"
    ]

    @staticmethod
    def size(scale):
        return ImageScale._sizes[scale]

    @staticmethod
    def name(scale):
        return ImageScale._names[scale]

    @staticmethod
    def fromName(name):
        try:
            return ImageScale._names.index(name.lower())
        except ValueError as e:
            return 0

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

    def shouldTranscodeSong(self, song, mode):

        srcpath = song[Song.path]
        ext = srcpath.lower()[-3:]

        if format == "raw" or ext == format:
            return False

        return True

    def _getTranscodeCommand(self, song, format, quality, nchannels, volume):

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
        """ scale the input image to the specified size.

        src_path: the image to resize
        tgt_path: the path to save the scaled image to
        scale: an ImageScale enum

        The image resolution is restricted to a small set of predefined
        dimensions. The scaling is guaranteed to preserve the aspect ratio.

        Square images are intended for icons, while the 16x9 aspect ratio
        images can be used for banners.
        """

        with self.fs.open(src_path, "rb") as rb:
            img = Image.open(rb)
            img.load()

        width, height = img.size

        tgt_width, tgt_height = ImageScale.size(scale)

        wscale = (tgt_width / float(width))
        hsize = int(wscale * height)
        img = img.resize((tgt_width, hsize), Image.BILINEAR)

        if img.size[1] < tgt_height:
            # pad with black pixels on the top and bottom
            d = tgt_height - img.size[1]
            padding = (0, int(d / 2), 0, round(d / 2))
            img = ImageOps.expand(img, padding)
        elif img.size[1] > tgt_height:
            # crop the image
            img = ImageOps.fit(img, (tgt_width, tgt_height))

        # the current FileSystem framework does not support seek()
        # img.save requires a seekable file object, and as the only
        # use case at present, this is a workaround until other use
        # cases are determined.
        with io.BytesIO() as bImg:
            img.save(bImg, format="png")
            bImg.seek(0)
            with self.fs.open(tgt_path, "wb") as wb:
                wb.write(bImg.read())

        return img.size

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

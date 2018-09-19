
"""
The transcode service enables file format conversion of media.

Audio files can be converted using FFmpeg

Image files can be processed using the pillow library.
"""
import os, sys
from ..dao.library import Song
from ..dao.filesys.filesys import FileSystem
from ..dao.transcode import FFmpeg
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
        """
        mode:
            default: transcode to mp3_320_2ch
            original: do not transcode

        todo: the env/app config should support specifing modes
            allow for: mono, stereo; 320, 256, 128; mp3, flac, etc;

        limit the available modes to a predefined list
        """

        if mode == "original":
            return False

        srcpath = song[Song.path]

        if mode == "non-mp3":
            return not srcpath.lower().endswith('.mp3')

        if mode == "non-ogg":
            return not srcpath.lower().endswith('.ogg')

        return True

    def transcodeSong(self, song, mode):
        """
        mode:
            original: do not transcode file
            non-mp3: only transcode if not already an mp3 file
            <kind>_<bitrate>_2ch: transcode all files to kind at bitrate.
                kind: mp3
                bitrate: for mp3, kilobytes per second, e.g. 256, 320
        """

        srcpath = song[Song.path]
        tgtpath = self.config.transcode.audio.tmp_path

        method = self.transcoder.transcode

        if mode == "original":
            return srcpath
        elif mode == "non-mp3" and srcpath.endswith(".mp3"):
            return srcpath
        elif mode == "non-ogg" and srcpath.endswith(".ogg"):
            return srcpath
        elif mode == "non-mp3":
            tgt_kind = "mp3"
            tgt_rate = 256
            tgt_channels = "2ch"
        elif mode == "non-ogg":
            tgt_kind = "ogg"
            tgt_rate = 256
            tgt_channels = "2ch"
            method = self.transcoder.transcode_ogg
        else:
            tgt_kind, tgt_rate, tgt_channels = mode.split("_")

        if not os.path.exists(tgtpath):
            os.makedirs(tgtpath)

        suffix = ".%s.%s.%s" % (tgt_rate, tgt_channels, tgt_kind)
        tgtpath = os.path.join(tgtpath, song[Song.id] + suffix)

        metadata = dict(
            artist=song[Song.artist],
            album=song[Song.album],
            title=song[Song.title]
        )

        volume = 1.0

        if not os.path.exists(tgtpath):
            opts = {
                "nchannels": 2,
                "volume": volume,
                "samplerate": 44100,
                "bitrate": int(tgt_rate),
                "metadata": {
                    "artist": song.get(Song.artist, "Unknown Artist"),
                    "title": song.get(Song.title, "Unknown Title"),
                    "album": song.get(Song.album, "Unknown Album"),
                }
            }
            with self.fs.open(srcpath, "rb") as rb:
                with self.fs.open(tgtpath, "wb") as wb:
                    method(rb, wb, **opts)

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

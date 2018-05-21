
import os, sys
from ..dao.library import Song
from .util import TranscodeServiceException, FFmpegEncoder
import logging

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
            return srcpath

        if not os.path.exists(tgtpath):
            os.makedirs(tgtpath)

        tgtpath = os.path.join(tgtpath, song[Song.id] + ".mp3")

        metadata = dict(
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
            bitrate = 0

        if not os.path.exists(tgtpath):
            self.encoder.transcode(srcpath,
                tgtpath,
                bitrate,
                vol=vol,
                metadata=metadata)

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
        img = Image.open(src_path)
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

        img.save(tgt_path)

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

        if not src_path or not os.path.exists(src_path):
            # when displaying album art as part of a resource, instead
            # of returning the default path, return a 303 redirect
            # to the url of the default art.
            logging.info("album art found: `%s`" % src_path)
            raise TranscodeServiceException(None, "file not found")

        dir, name  = os.path.split(src_path)
        name, _ = os.path.splitext(name)
        name = "%s.%s.png" % (name, ImageScale.name(scale))
        tgt_path = os.path.join(dir, name)

        self.scaleImage(src_path, tgt_path, scale)

        return tgt_path

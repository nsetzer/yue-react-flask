
import sys
import unittest

from .filesys.filesys import FileSystem
from .db import main_test
from .transcode import find_ffmpeg, FFmpeg

class FilesResourceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ffmpeg_path = find_ffmpeg()

        if cls.ffmpeg_path is None:
            raise Exception("FFmpeg not found")

        cls.fs = FileSystem()

    def test_transcode(self):

        transcoder = FFmpeg(self.ffmpeg_path)

        opts = {
            "nchannels": 2,
            "volume": 0.5,
            "samplerate": 44100,
            "bitrate": 256,
            "metadata": {
                "artist": "Test",
                "title": "Test",
                "album": "Test",
            }
        }

        # local to local
        pathA = "test/r160.mp3"
        pathB = "test/r160_out.mp3"
        with self.fs.open(pathA, "rb") as rb:
            with self.fs.open(pathB, "wb") as wb:
                transcoder.transcode(rb, wb, **opts)

        _, _, size, mtime = self.fs.file_info(pathB)
        self.assertTrue(size > 0)

        # local to mem
        pathA = "test/r160.mp3"
        pathB = "mem://test/r160_out.mp3"
        with self.fs.open(pathA, "rb") as rb:
            with self.fs.open(pathB, "wb") as wb:
                transcoder.transcode(rb, wb, **opts)

        _, _, size, mtime = self.fs.file_info(pathB)
        self.assertTrue(size > 0)

        # mem to local
        pathA = "mem://test/r160_out.mp3"
        pathB = "test/r160_out.mp3"
        with self.fs.open(pathA, "rb") as rb:
            with self.fs.open(pathB, "wb") as wb:
                transcoder.transcode(rb, wb, **opts)

        _, _, size, mtime = self.fs.file_info(pathB)
        self.assertTrue(size > 0)

if __name__ == '__main__':
    main_test(sys.argv, globals())

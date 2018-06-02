import os
import sys
import unittest
import json
import time

from ..dao.db import main_test
from ..dao.library import Song
from ..app import TestApp

from .transcode_service import ImageScale

from PIL import Image

class FilesResourceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = TestApp(cls.__name__)

        cls.service = cls.app.transcode_service

        img1 = "./test/blank-32-32.png"
        img2 = "./test/blank-32-16.png"
        img3 = "./test/blank-16-32.png"

        # create three test images that demonstrate the three possible cases
        # the expected input is either a square image, or an image longer
        # in one of the dimensions. regardless of the input the output
        # should have the expected dimensions

        img = Image.new("RGB", (32, 32))
        img.save(img1)

        img = Image.new("RGB", (32, 16))
        img.save(img2)

        img = Image.new("RGB", (16, 32))
        img.save(img3)

        cls.images = [img1, img2, img3]

    @classmethod
    def tearDownClass(cls):
        cls.app.tearDown()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_001a_transcode_song(self):

        song = {
            Song.id: "transcode-test",
            Song.artist: "Test",
            Song.album: "Test",
            Song.title: "Test",
            Song.path: "./test/r160.mp3",
        }

        expected_path = "./test/transcode-test.256.2ch.mp3"
        if os.path.exists(expected_path):
            os.remove(expected_path)

        path = self.service.transcodeSong(song, "mp3_256_2ch")

        # the transcode process should produce a new file with non-zero size
        self.assertNotEqual(song[Song.path], path)
        self.assertTrue(os.path.exists(path))
        st = os.stat(path)
        self.assertTrue(st.st_size > 0)

    def test_002a_resize_image_large(self):
        tgt_path = "./test/blank-out.png"
        scale = ImageScale.LARGE
        for src_path in self.images:
            w, h = self.service.scaleImage(src_path, tgt_path, scale)
            self.assertEqual((w, h), ImageScale.size(scale))
            self.assertTrue(os.path.exists(tgt_path))

    def test_002b_resize_image_medium(self):
        tgt_path = "./test/blank-out.png"
        scale = ImageScale.MEDIUM
        for src_path in self.images:
            w, h = self.service.scaleImage(src_path, tgt_path, scale)
            self.assertEqual((w, h), ImageScale.size(scale))
            self.assertTrue(os.path.exists(tgt_path))

    def test_002c_resize_image_small(self):
        tgt_path = "./test/blank-out.png"
        scale = ImageScale.SMALL
        for src_path in self.images:
            w, h = self.service.scaleImage(src_path, tgt_path, scale)
            self.assertEqual((w, h), ImageScale.size(scale))
            self.assertTrue(os.path.exists(tgt_path))

    def test_002d_resize_image_landscape(self):
        tgt_path = "./test/blank-out.png"
        scale = ImageScale.LANDSCAPE
        for src_path in self.images:
            w, h = self.service.scaleImage(src_path, tgt_path, scale)
            self.assertEqual((w, h), ImageScale.size(scale))
            self.assertTrue(os.path.exists(tgt_path))

    def test_002e_resize_image_landscape_small(self):
        tgt_path = "./test/blank-out.png"
        scale = ImageScale.LANDSCAPE_SMALL
        for src_path in self.images:
            w, h = self.service.scaleImage(src_path, tgt_path, scale)
            self.assertEqual((w, h), ImageScale.size(scale))
            self.assertTrue(os.path.exists(tgt_path))

    def test_003_transcode_art(self):

        song = {Song.art_path: self.images[0]}

        path = self.service.getScaledAlbumArt(song, ImageScale.SMALL)

        name = ImageScale.name(ImageScale.SMALL)
        self.assertTrue(path.endswith(".%s.png" % name))
        self.assertTrue(os.path.exists(path))

if __name__ == '__main__':
    main_test(sys.argv, globals())


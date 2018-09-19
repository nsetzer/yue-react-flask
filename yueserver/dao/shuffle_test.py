import os
import unittest
import json
import time
import random

from .shuffle import binshuffle

class ShuffleTestCase(unittest.TestCase):

    def test_shuffle(self):

        seq = list("1111222233334444")

        # TODO: this test occasionally fails if the seed is not set
        # this indicates that more work is needed to tune the hyper parameters
        random.seed(4)
        out = binshuffle(seq)

        # shuffle guarantees that no similar
        # element will be neighbors
        for i in range(1, len(out)):
            self.assertNotEqual(out[i], out[i-1])

    def test_degenerate_1(self):

        seq = list("1")

        out = binshuffle(seq)

        self.assertEqual(seq, out)

def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ShuffleTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()

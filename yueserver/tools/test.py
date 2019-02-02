import os, sys
import pkgutil
import unittest
import shutil
import fnmatch
import argparse
import logging

from yueserver.dao.util import CaptureOutput

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

class Tests(object):

    def run(self, pattern, verbose):
        test_loader = unittest.defaultTestLoader
        test_runner = unittest.TextTestRunner(verbosity=verbose)
        pattern = pattern + "_test.py"
        test_suite = test_loader.discover(".", pattern=pattern)
        with CaptureOutput():
            return test_runner.run(test_suite)

class Coverage(object):
    """

    INSTALL:
      pip install coverage
    """

    def run(self):
        self._exec("coverage run " + __file__)
        self._exec("coverage html  --omit='/usr/*,*_test*.py'")

    def _exec(self, *args):
        cmd = ' '.join(args)
        print(cmd)
        os.system(cmd)

def main():
    """run server tests"""

    package = "server"

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='enable verbose logging')
    parser.add_argument('-p', '--pattern', dest='pattern', default="*",
                        help='filter for tests to run')

    parser.add_argument('--mode', dest='mode', default="test",
                        help='test or coverage')

    args = parser.parse_args()

    logger = logging.getLogger()
    logger.disabled = True

    if "coverage".startswith(args.mode):
        Coverage().run()
    else:
        Tests().run(args.pattern, 2 if args.verbose else 1)

if __name__ == '__main__':
    main()

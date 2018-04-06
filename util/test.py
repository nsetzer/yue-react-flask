import os, sys
import pkgutil
import unittest
import shutil
import fnmatch
import argparse
import logging

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

class Tests(object):

    def run(self, verbose):
        test_loader = unittest.defaultTestLoader
        test_runner = unittest.TextTestRunner(verbosity=verbose)
        # test_suite = collect_test_suite(package,args.pattern);
        test_suite = test_loader.discover(".", pattern="test_*.py")
        return test_runner.run(test_suite)

class Coverage(object):
    """

    INSTALL:
      pip install coverage
    """

    def run(self):
      self._exec("coverage run " + __file__)
      self._exec("coverage html  --omit='/usr/*,*test_*.py'")

    def _exec(self,*args):
      cmd=' '.join(args)
      print(cmd)
      os.system(cmd)

def main():
    """run server tests"""

    package = "server"

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='enable verbose logging')
    parser.add_argument('-p', '--pattern', dest='pattern', default="*",
                        help='filter for tests ot run')

    parser.add_argument('--mode', dest='mode', default="test",
                        help='test or coverage')

    args = parser.parse_args()

    logger = logging.getLogger()
    logger.disabled = True

    if "coverage".startswith(args.mode):
        Coverage().run()
    else:
        Tests().run(2 if args.verbose else 1)



if __name__ == '__main__':
    main()

import os, sys
import pkgutil
import unittest
import shutil
import fnmatch
import argparse

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

def main():
    """run server tests"""

    package = "server"

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='enable verbose logging')
    parser.add_argument('-p', '--pattern', dest='pattern', default="*",
                        help='filter for tests ot run')

    args = parser.parse_args()

    path = os.path.join(os.getcwd(), "test.db")
    os.environ["DATABASE_URL"] = "sqlite:///" + path
    os.environ["ENV"] = "testing"
    os.environ["DEBUG"] = "True" if args.verbose else "False"

    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    # test_suite = collect_test_suite(package,args.pattern);
    test_suite = test_loader.discover(".", pattern="test_*.py")

    return test_runner.run(test_suite)


if __name__ == '__main__':
    main()

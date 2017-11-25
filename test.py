import os, sys
import pkgutil
import unittest
import shutil
import fnmatch
import argparse

def collect_test_suite(pkgName,pattern):
    """
    hack: implementation of discover for python 2.6
    for python 2.7 and 3+ use test_loader.discover

    assumes that python files containing tests start with test_
      and classes start with Test,
      and of those classes, the methods start with test_
    """

    file_prefix = "test_"
    test_prefix = "test_" # prefix for function names
    cls_suffix  = "TestCase"

    # fix the given pattern to accept the following rules:
    #   - an asterisk '*' matches any number of characters
    #   - if prefixed with '^' the test must start with the next character
    #   - if suffixed with '$' the test must end with the preceding character
    #   - all tests begin with 'test_' and is ignored in pattern matching
    if pattern.startswith("^"):
        pattern = test_prefix + pattern[1:]
    elif not pattern.startswith("*"):
        pattern = test_prefix + "*" + pattern

    if pattern.endswith("$"):
        pattern = pattern[:-1]
    elif not pattern.endswith("*"):
        pattern += "*"

    if pattern == "*":
        pattern= test_prefix + pattern

    pkg = __import__(pkgName)
    suite = unittest.TestSuite()
    for importer, modname, ispkg in pkgutil.walk_packages(pkg.__path__):
        module = __import__(pkgName+'.'+modname, fromlist="dummy")
        for clsName, cls in vars(module).items():
            if clsName.endswith(cls_suffix):
                for testName in dir(cls):
                  if fnmatch.fnmatch(testName,pattern):
                    suite.addTest(cls(testName))
                  elif testName.startswith(test_prefix):
                    sys.stderr.write("skipping test %s.\n"%testName)
    return suite

def main():
    """run server tests"""

    package = "server"

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='enable verbose logging')
    parser.add_argument('-p', '--pattern', dest='pattern', default="*",
                        help='filter for tests ot run')

    args = parser.parse_args()

    path=os.path.join(os.getcwd(),"test.db")
    os.environ["DATABASE_URL"] = "sqlite:///" + path
    os.environ["ENV"] = "testing"
    os.environ["DEBUG"] = "True" if args.verbose else "False"

    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    test_suite = collect_test_suite(package,args.pattern);

    return test_runner.run(test_suite)

if __name__ == '__main__':
    main()
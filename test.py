import os, sys
import pkgutil
import unittest
import shutil
import fnmatch
import argparse

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from server.config import Config

def configure_test_database(env_config):
    index = __import__("server.index").index
    config = __import__("server.cli.config").cli.config

    db = index.db
    dbtables = index.dbtables

    config.db_drop_all(db, dbtables)
    config.db_init_test(db, dbtables, env_config)

def main():
    """run server tests"""

    package = "server"

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='enable verbose logging')
    parser.add_argument('-p', '--pattern', dest='pattern', default="*",
                        help='filter for tests ot run')
    parser.add_argument('--config', type=str,
                    default="config/test/application.yml",
                    help='application config path')

    args = parser.parse_args()

    cfg = Config.init(args.config)

    path = os.path.join(os.getcwd(), "test.db")
    #os.environ["DATABASE_URL"] = "sqlite:///" + path
    #os.environ["ENV"] = "testing"
    #os.environ["DEBUG"] = "True" if args.verbose else "False"

    configure_test_database("config/test/env.yml")

    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    # test_suite = collect_test_suite(package,args.pattern);
    test_suite = test_loader.discover(".", pattern="test_*.py")

    return test_runner.run(test_suite)


if __name__ == '__main__':
    main()

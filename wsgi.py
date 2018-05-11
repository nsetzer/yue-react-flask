
import sys

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from server.app import main

if __name__ == '__main__':
    main()


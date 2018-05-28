
import sys

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from server.app import parseArgs, getApp

args = parseArgs(sys.argv, "production")

app = getApp(args.config, args.profile)

if __name__ == '__main__':
    app.run()


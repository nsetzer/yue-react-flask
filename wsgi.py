
import sys
import logging

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

try:
    from yueserver.app import parseArgs, getApp
except ImportError as e:
    if not hasattr(sys, 'real_prefix'):
        # guess that the user forgot to activate their venv
        sys.stderr.write("not inside a virtual environment")
    raise e

debugLogging = __name__ == '__main__'
args = parseArgs(sys.argv, "production")

app = getApp(args.config, args.profile, debugLogging)

if __name__ == '__main__':
    app.run()


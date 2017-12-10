
import os, sys

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from server.app import app

port = 4200
if "PORT" in os.environ:
    port = int(os.environ["PORT"])

app.run(host='0.0.0.0', port=port)

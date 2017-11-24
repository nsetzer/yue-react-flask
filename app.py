
import os, sys
from server.app import app

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

port = 4200
if "PORT" in os.environ:
    port = int(os.environ["PORT"])

app.run(host='localhost', port=port)

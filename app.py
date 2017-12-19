
import os, sys
import argparse

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from server.config import Config

parser = argparse.ArgumentParser(description='yue server')
parser.add_argument('--config', type=str,
                    default="config/production/application.yml",
                    help='application config path')

args = parser.parse_args()

Config.init(args.config)

from server.app import app

port = 4200
if "PORT" in os.environ:
    port = int(os.environ["PORT"])

app.run(host='0.0.0.0', port=port)


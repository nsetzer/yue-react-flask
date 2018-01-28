
import os, sys
import argparse
import ssl
import logging
from logging.handlers import RotatingFileHandler

if (sys.version_info[0] == 2):
    raise RuntimeError("python2 not supported")

from server.config import Config

parser = argparse.ArgumentParser(description='yue server')
parser.add_argument('--config', type=str,
                    default="config/development/application.yml",
                    help='application config path')

args = parser.parse_args()

cfg = Config.init(args.config)

# configure ssl
context = None
if os.path.exists(cfg.ssl.private_key) and os.path.exists(cfg.ssl.certificate):
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(cfg.ssl.certificate, cfg.ssl.private_key)

# configure logging
logging.basicConfig(level=cfg.logging.level)
if not os.path.exists(cfg.logging.directory):
    os.makedirs(cfg.logging.directory)
log_path = os.path.join(cfg.logging.directory, cfg.logging.filename)
handler = RotatingFileHandler(log_path,
    maxBytes=cfg.logging.max_size,
    backupCount=cfg.logging.num_backups)
handler.setLevel(cfg.logging.level)
logging.getLogger().addHandler(handler)

from server.app import app

app.logger.addHandler(handler)
app.logger.setLevel(cfg.logging.level)

app.logger.info("config: %s", args.config)
app.logger.info("database: %s", cfg.database.url)

port = 4200
if "PORT" in os.environ:
    port = int(os.environ["PORT"])

app.run(host='0.0.0.0', port=port, ssl_context=context)


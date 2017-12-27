
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
                    default="config/production/application.yml",
                    help='application config path')

args = parser.parse_args()

cfg = Config.init(args.config)

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

if __name__ == '__main__':
    app.run()


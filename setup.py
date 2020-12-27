

import os, sys
from setuptools import setup, Command
from distutils.sysconfig import get_python_lib
import unittest
import shutil
import subprocess
from datetime import datetime

#from yueserver.app import YueApp, generate_client
from yueserver.config import Config

#app = YueApp(Config.null())
#generate_client(app)

def collect_package(root):

    pkgs = [root]
    for path, dirs, files in os.walk(root):
        for name in dirs:
            if name != "__pycache__":
                pkgs.append(path.replace("/", ".") + "." + name)

    return pkgs

pkgs = collect_package("yueserver")
pkgs += collect_package("yueclient")

for pkg in pkgs:
    print(pkg)

entry_points = [
    "ymgr=yueserver.tools.manage:main",
    "syn=yueserver.sync.sync:main",
]

short_version = "0.1.0"
long_version = short_version

commit = None
proc = subprocess.run(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE)
if proc.returncode == 0:
  commit = proc.stdout.decode("utf-8").strip()

if commit:
  long_version += "-" + commit[:8]

branch = None
proc = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], stdout=subprocess.PIPE)
if proc.returncode == 0:
  branch = proc.stdout.decode("utf-8").strip()

if branch:
  long_version += "-" + branch.replace("/","-")

with open("yueserver/__init__.py", "w") as wf:
  wf.write("__version__ = %r\n" % long_version)
  wf.write("__branch__ = %r\n" % branch)
  wf.write("__githash__ = %r\n" % commit)
  wf.write("__date__ = '%s'\n" % datetime.now())

setup(name="yueserver",
      version=short_version,
      description="Yue Music Server",
      packages=pkgs,
      install_requires=[],
      data_files=[],
      entry_points={"console_scripts": entry_points},
      )

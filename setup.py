

import imp, os, sys
from setuptools import setup, Command
from distutils.sysconfig import get_python_lib
import unittest
import shutil

from yueserver.app import YueApp, generate_client
from yueserver.config import Config

app = YueApp(Config.null())
generate_client(app)

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
    "ysync=yueserver.tools.sync2:main",
    "syn=yueserver.tools.sync2:main",
]

setup(name="yueserver",
      version='0.1',
      description="Yue Music Server",
      packages=pkgs,
      install_requires=[],
      data_files=[],
      entry_points={"console_scripts": entry_points},
      )


import os, sys
from flask import request, jsonify, g, send_file
from ..index import app, db, dbtables
from .util import requires_auth, requires_auth_feature, httpError
from stat import S_ISDIR, S_ISREG, S_IRGRP

from ..config import Config
"""
curl -v -u admin:admin "http://localhost:4200/api/fs/default"
curl -v -u admin:admin "http://localhost:4200/api/fs/default"
"""

@app.route('/api/fs/<root>/path/', defaults={'path': ''})
@app.route('/api/fs/<root>/path/<path:path>')
@requires_auth_feature("read_filesystem")
def fs_get_path(root, path):

    if root != "default":
        return httpError(400, "invalid root `%s`" % root)

    # application config should define a number of valid roots
    # that can be listed.
    os_root = Config.instance().filesystem.media_root
    path = os.path.join(os_root, path)


    if not os.path.exists(path):
        return httpError(404, "path does not exist")

    if os.path.isfile(path):
        return send_file(path)

    return list_directory(root, os_root, path)

@app.route('/api/fs/roots')
@requires_auth_feature("read_filesystem")
def fs_get_routes():
    # todo this should be a list of names
    return jsonify(result=["default", ])

def list_directory(fs_name, root, path):
    """
    check for .yueignore in the root, or in the given path
    use to load filters to remove elements from the response
    """

    parent, _ = os.path.split(path)
    if not parent.startswith(root):
        parent = root

    files = []
    dirs = []
    for name in os.listdir(path):
        pathname = os.path.join(path, name)
        st = os.stat(pathname)
        mode = st.st_mode

        if not (mode & S_IRGRP):
            continue

        if S_ISDIR(mode):
            dirs.append(name)
        elif S_ISREG(mode):
            files.append({"name": name, "size": st.st_size})

    files.sort(key=lambda f: f['name'])
    dirs.sort()

    def trim_path(p):
        p = p.replace("\\","/")
        if p.startswith(root):
            p = p[len(root):]
        while p.startswith("/"):
            p = p[1:]
        return p

    result = {
        "name": fs_name,
        "path": trim_path(path),
        "parent": trim_path(parent),
        "files": files,
        "directories": dirs
    }
    return jsonify(result=result)


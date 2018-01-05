
import os, sys
from flask import request, jsonify, g, send_file
from ..index import app, db, dbtables
from .util import requires_auth, httpError
from stat import S_ISDIR, S_ISREG, S_IRGRP

from ..config import Config
"""
curl -v -u admin:admin "http://localhost:4200/api/fs/default"
curl -v -u admin:admin "http://localhost:4200/api/fs/default"
"""

"""

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
<head><title>Index of libs-release-local/com/cogito/compute-library</title>
</head>
<body>
<h1>Index of libs-release-local/com/cogito/compute-library</h1>
<pre>Name                     Last modified      Size</pre><hr/>
<pre>
<a href="../">../</a>
<a href="3.10.0/">3.10.0/</a>                   23-May-2016 15:41    -
</pre>
"""

@app.route('/api/fs/<root>/path/', defaults={'path': ''})
@app.route('/api/fs/<root>/path/<path:path>')
@requires_auth
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
@requires_auth
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
        if p.startswith(root):
            p = p[len(root):]
        while p.startswith("/"):
            p = p[1:]
        return p

    print(parent, path, trim_path(path))
    result = {
        "name": fs_name,
        "path": trim_path(path),
        "parent": trim_path(parent),
        "files": files,
        "directories": dirs
    }
    return jsonify(result=result)


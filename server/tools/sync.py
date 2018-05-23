
import os, posixpath, sys

def _check(client, root, remote_base, local_base):
    """
    returns 4 lists:
        a list of folders which need to be synced down
        a list of folders which need to be synced up
        a list of files which need to be synced down
        a list of files which need to be synced up
    """
    response = client.files_get_path(root, remote_base)

    if response.status_code == 404:
        data = {'directories':[], 'files':[]}
    else:
        data = response.json()['result']

    # data structures to easily process remote files
    directories = set(data['directories'])
    files = {d['name']:(d['mtime'], d['size']) for d in data['files']}

    uld = [] # directories to sync up
    dld = [] # directories to sync down
    ulf = [] # files to sync up
    dlf = [] # files to sync down

    if os.path.exists(local_base):

        for entry in os.scandir(local_base):
            if entry.is_file():

                local_path = os.path.join(local_base, entry.name)
                st = entry.stat()
                local_size = st.st_size
                local_mtime = int(st.st_mtime)

                if entry.name in files:
                    remote_mtime, remote_size = files[entry.name]
                    if local_mtime < remote_mtime:
                        # print("remote is newer: %s" % entry.name)
                        dlf.append((entry.name, remote_mtime, remote_size))
                    elif local_mtime > remote_mtime:
                        # print("remote is older: %s" % entry.name)
                        ulf.append((entry.name, local_mtime, local_size))
                    # else:
                    #     print("files are synced: %s" % entry.name)

                    del files[entry.name]
                else:
                    # print("no remote match: %s" % entry.name)
                    ulf.append((entry.name, local_mtime, local_size))
            elif entry.is_dir():

                if entry.name in directories:
                    dld.append(entry.name)
                    directories.remove(entry.name)
                else:
                    uld.append(entry.name)

            elif entry.is_symlink():
                # don't want to support symlinks at this time
                pass

    for name, (remote_mtime, remote_size) in files.items():
        # print("no local match: %s" % name)
        dlf.append((name, remote_mtime, remote_size))

    for name in directories:
        dld.append(name)

    return dld, uld, dlf, ulf

def _pull(client, root, remote_base, local_base, dlf):
    # download all files marked for download
    for name, mtime, size in dlf:
        print("pull: %s/%s/%s" % (client.host(), root,
                    posixpath.join(remote_base, name)))
        local_path = os.path.join(local_base, name)
        remote_path = os.path.join(remote_base, name)
        response = client.files_get_path(root, remote_path, stream=True)
        with open(local_path, "wb") as wb:
            for chunk in response.stream():
                wb.write(chunk)
        os.utime(local_path, (mtime, mtime))

def _push(client, root, remote_base, local_base, ulf):
    # upload all files marked for upload
    for name, mtime, size in ulf:
        print("push: %s" % (name,))
        local_path = os.path.join(local_base, name)
        remote_path = os.path.join(remote_base, name)
        with open(local_path, "rb") as rb:
            response = client.files_upload(root, remote_path, rb,
                mtime=mtime)

class SyncManager(object):
    """docstring for SyncClient"""
    def __init__(self, client, name, local_root, dryrun):
        super(SyncManager, self).__init__()

        self.client = client
        self.name = name
        self.dryrun = dryrun

        self.local_root = local_root
        self.remote_base = None
        self.local_base = None

        self.dld = []
        self.uld = []
        self.dlf = []
        self.ulf = []

    def _check(self, remote_base, local_base):

        self.remote_base = remote_base
        self.local_base = local_base

        dld, uld, dlf, ulf = _check(self.client, self.name,
            remote_base, local_base)

        # append

        for name in dld:
            a = posixpath.join(remote_base, name)
            b = os.path.join(local_base, name)
            self.uld.append((a,b))

        for name in uld:
            a = posixpath.join(remote_base, name)
            b = os.path.join(local_base, name)
            self.uld.append((a,b))

        # update
        self.dlf = dlf
        self.ulf = ulf

    def _push(self):

        if self.dryrun:
            for f, _, _ in self.ulf:
                print("push: %s" % (os.path.join(self.local_base, f)))
            return

        _push(self.client, self.name,
            self.remote_base, self.local_base, self.ulf)
        self.ulf = []

    def _pull(self):

        if self.dryrun:
            for f, _, _ in self.dlf:
                print("pull: %s/%s/%s" % (self.client.host(), self.name,
                    posixpath.join(self.remote_base, f)))
            return

        _pull(self.client, self.name,
            self.remote_base, self.local_base, self.dlf)
        self.dlf = []

    def next(self,pull=True, push=True):

        if self.remote_base is None and self.local_base is None:
            # first time this is run, scan the root directory
            self._check("", self.local_root)
        elif pull and self.dld:
            # scan directories to download
            self._check(*self.dld.pop(0))
        elif push and self.uld:
            # scan directires to upload
            self._check(*self.uld.pop(0))
        else:
            return False

        if pull:
            self._pull()

        if push:
            self._push()

        return bool(self.dld or self.uld)



import os, posixpath, sys
import argparse
import logging
import json
import time

from ..app import connect

def _check(client, root, remote_base, local_base, match_size=False):
    """
    foo : sync files, even if the size is equal
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

                    if not match_size and local_size == remote_size:
                        # the files are the same if the size is equal
                        logging.debug("file size equal: %s" % entry.name)
                    elif local_mtime == remote_mtime:
                        # if the time is the same, there is nothing to sync
                        logging.debug("files are synced: %s" % entry.name)
                    elif local_mtime < remote_mtime:
                        # download files where remote is newer
                        logging.debug("remote is newer: %s" % entry.name)
                        dlf.append((entry.name, remote_mtime, remote_size))
                    elif local_mtime > remote_mtime:
                        # upload files where remote is older
                        logging.debug("remote is older: %s" % entry.name)
                        ulf.append((entry.name, local_mtime, local_size))
                    elif local_size != remote_size:
                        # unclear whether to upload or download
                        print("size differs: %s/%s" % (local_base, entry.name))

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

def _pull(client, root, remote_base, local_base, dlf, dryrun):
    # download all files marked for download
    for name, mtime, size in dlf:
        logging.info("pull: %s/api/fs/%s/path/%s" % (client.host(), root,
                    posixpath.join(remote_base, name)))
        if dryrun:
            continue
        local_path = os.path.join(local_base, name)
        remote_path = posixpath.join(remote_base, name)
        response = client.files_get_path(root, remote_path, stream=True)
        parent, _ = os.path.split(local_path)
        if not os.path.exists(parent):
            os.makedirs(parent)
        with open(local_path, "wb") as wb:
            for chunk in response.stream():
                wb.write(chunk)
        os.utime(local_path, (mtime, mtime))

def _push(client, root, remote_base, local_base, ulf, dryrun):
    # upload all files marked for upload
    for name, mtime, size in ulf:
        logging.info("push: %s/%s => %s/api/fs/%s/%s/%s" % (local_base,name,
            client.host(), root, remote_base, name))
        if dryrun:
            continue
        local_path = os.path.join(local_base, name)
        remote_path = posixpath.join(remote_base, name)
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


        logging.info("scan: %s <=> %s/api/fs/%s/path/%s" % (self.local_base,
                self.client.host(), self.name, self.remote_base))

        dld, uld, dlf, ulf = _check(self.client, self.name,
            remote_base, local_base)

        # append

        for name in dld:
            a = posixpath.join(remote_base, name)
            b = os.path.join(local_base, name)
            self.dld.append((a,b))

        for name in uld:
            a = posixpath.join(remote_base, name)
            b = os.path.join(local_base, name)
            self.uld.append((a,b))

        # update
        self.dlf = dlf
        self.ulf = ulf

        self._force = False

    def _push(self):
        _push(self.client, self.name,
            self.remote_base, self.local_base, self.ulf, self.dryrun)
        self.ulf = []

    def _pull(self):
        _pull(self.client, self.name,
            self.remote_base, self.local_base, self.dlf, self.dryrun)
        self.dlf = []

    def setDirectory(self, dir_path):

        if not dir_path.startswith(self.local_root):
            raise Exception("not a subdirectory: %s or %s" % (
                dir_path, self.local_root))

        # compare the current working directory (dir_path), with
        # the saved local path. remove path components to determine
        # what components are common. the left over components
        # can then be used with the remote base and local base as
        # the initial directory to start scanning.

        a = dir_path.replace("\\", "/").split("/")
        b = self.local_root.replace("\\", "/").split("/")
        while a and b and a[0] == b[0]:
            b.pop(0)
            a.pop(0)
        if b:
            raise Exception("%s not valid" % dir_path)

        self.remote_base = '/'.join(a)
        self.local_base = dir_path

        self._force = True

    def next(self,pull=True, push=True):

        if self.remote_base is None and self.local_base is None:
            # first time this is run, scan the root directory
            self._check("", self.local_root)
        elif self.dld:
            # scan directories to download
            self._check(*self.dld.pop())
        elif self.uld:
            # scan directires to upload
            self._check(*self.uld.pop())
        elif self._force:
            # force a re-check
            self._check(self.remote_base, self.local_base)
            self._force = False
        else:
            return False

        if pull:
            self._pull()

        if push:
            self._push()

        return bool(self.dld or self.uld)

def getDefaultConfigDirectory():

    if os.name == 'nt':
        base = os.environ["USERPROFILE"]
    else:
        base = os.environ["HOME"]

    return os.path.join(base, ".config", "yueserver")

def prefix_match(registerd_paths, path):

    # longest prefix match on local path
    for name, base in sorted(registerd_paths.items(),
      key=lambda x: len(x[1]) , reverse=True):
        if path.startswith(base):
            return (name, base)
    return (None, "")

def _get_config(args):

    cfg = {}
    if os.path.exists(args.config):
        try:
            with open(args.config, "r") as rf:
                cfg = json.load(rf)
        except:
            pass

        for key in ['username', 'password']:
            if getattr(args, key) is None:
                setattr(args, key, cfg[key])

        if 'host' in cfg:
            args.host = cfg['host']

    elif not os.path.exists(args.configdir):
        os.makedirs(args.configdir)

    if 'items' not in cfg:
        cfg['items'] = {}

    return cfg

def _sync(args):

    cfg = _get_config(args)

    if args.username is None:
        sys.stderr.write("username not provided")
        sys.exit(1)

    if args.password is None:
        sys.stderr.write("password not provided")
        sys.exit(1)

    if len(cfg['items']) == 0:
        sys.stderr.write("invalid config")
        sys.exit(1)

    pwd = os.path.abspath(args.pwd)
    name, local_root = prefix_match(cfg['items'], pwd)
    client = connect(args.host, args.username, args.password)
    mgr = SyncManager(client, name, local_root, args.dryrun)
    mgr.setDirectory(pwd)

    cont = True
    while cont:
        cont = mgr.next(pull=args.pull, push=args.push) and args.recursive

def _copy(args):
    """ copy a file to/from a remote server
    """
    def usage():
        sys.stderr.write("usage:\n")
        sys.stderr.write("copy /path/to/file server://<root>/<path/to/file>\n")
        sys.stderr.write("copy server://<root>/<path/to/file> /path/to/file\n")
        sys.exit(1)

    cfg = _get_config(args)

    if args.username is None:
        sys.stderr.write("username not provided")
        usage()

    if args.password is None:
        sys.stderr.write("password not provided")
        usage()

    client = connect(args.host, args.username, args.password)

    if args.src_file.startswith("server://"):
        root, path = args.src_file.replace("server://", "").split("/", 1)


        if args.dryrun:
            sys.stdout.write("copy %s/api/fs/%s/path/%s => %s\n" % (
                client.host(), root, path, args.dst_file))
        elif args.dst_file == "-":
            response = client.files_get_path(root, path, stream=True)
            for chunk in response.stream():
                sys.stdout.buffer.write(chunk)
        else:
            response = client.files_get_path(root, path, stream=True)
            with open(args.dst_file, "wb") as wb:
                for chunk in response.stream():
                    wb.write(chunk)

    elif args.dst_file.startswith("server://"):
        root, path = args.dst_file.replace("server://", "").split("/", 1)

        if args.dryrun:
            sys.stdout.write("copy %s => %s/api/fs/%s/path/%s\n" % (
                args.src_file, client.host(), root, path,))
        elif args.src_file == "-":
            response = client.files_upload(root, path, sys.stdin.buffer)
        else:
            st = os.stat(args.src_file)
            mtime = int(st.st_mtime)

            with open(args.src_file, "rb") as rb:
                response = client.files_upload(root, path, rb, mtime=mtime)

    else:
        usage()

def _list(args):

    def usage():
        sys.stderr.write("usage:\n")
        sys.stderr.write("list server://<root>/<path/to/directory>\n")
        sys.exit(1)

    cfg = _get_config(args)

    if args.username is None:
        sys.stderr.write("username not provided")
        usage()

    if args.password is None:
        sys.stderr.write("password not provided")
        usage()

    client = connect(args.host, args.username, args.password)

    if not args.path.startswith("server://"):
        usage()
    else:
        root, path = args.path.replace("server://", "").split("/", 1)
        response = client.files_get_path(root, path)

        if response.status_code == 404:
            sys.stderr.write("not found: %s" % args.path)
            sys.exit(1)

        else:
            data = response.json()['result']

            for dirname in data['directories']:
                sys.stdout.write("%s%s\n" % (" " * (18+13), dirname))

            for item in data['files']:


                ftime = time.localtime(item['mtime'])
                fdate = time.strftime('%Y-%m-%d %H:%M:%S', ftime)

                sys.stdout.write("%s %10d %s\n" % (
                    fdate, int(item['size']), item['name']))

def _config(args):

    cfg = _get_config(args)

    if os.path.exists(args.local_root):
        cfg['items'][args.name] = os.path.abspath(args.local_root)

    if args.username is not None:
        cfg['username'] = args.username

    if args.password is not None:
        cfg['password'] = args.password

    if args.host != "https://localhost:4200":
        cfg['host'] = args.host

    with open(args.config, "w") as wf:
        json.dump(cfg, wf, sort_keys=True, indent=4)

def _list_config(args):

    cfg = _get_config(args)

    if 'username' in cfg:
        sys.stdout.write("username: %s\n" % cfg['username'])

    if 'password' in cfg:
        sys.stdout.write("password: hunter2\n")

    if 'host' in cfg:
        sys.stdout.write("host: %s\n" % cfg['host'])

    for name, path in sorted(cfg['items'].items()):
        sys.stdout.write("%s: %s\n" % (name, path))

def _remove_config(args):

    cfg = _get_config(args)

    if args.name in cfg['items']:
        del cfg['items'][args.name]

    with open(args.config, "w") as wf:
        json.dump(cfg, wf, sort_keys=True, indent=4)

def parseArgs(argv):
    """
    argv: sys.argv or equivalent
    """

    configd = getDefaultConfigDirectory()

    parser = argparse.ArgumentParser(description='Sync tool')

    parser.add_argument('--username', default=None,
                    help='username')

    parser.add_argument('--password', default=None,
                    help='password')

    parser.add_argument('--host', dest='host',
                    default="https://localhost:4200",
                    help='the database connection string')

    parser.add_argument('-v', '--verbose', dest='verbose',
                    action='store_true',
                    help='enable verbose logging')

    parser.add_argument('--dryrun', dest='dryrun',
                    action='store_true',
                    help='print changes without taking any action')

    parser.add_argument('--config', dest='configdir',
                    default = configd,
                    help='settings directory')

    subparsers = parser.add_subparsers()

    sync_parser = subparsers.add_parser("sync")
    sync_parser.set_defaults(func=_sync, pull=True, push=True)
    sync_parser.add_argument('-r', '--recursive',
        action='store_true',
        help='descend into directories')
    sync_parser.add_argument('pwd', default = os.getcwd(),
        metavar="directory",
        help='local dir to sync (current director)')

    pull_parser = subparsers.add_parser("pull")
    pull_parser.set_defaults(func=_sync, pull=True, push=False)
    pull_parser.add_argument('-r', '--recursive',
        action='store_true',
        help='descend into directories')
    pull_parser.add_argument('pwd', default = os.getcwd(),
        metavar="directory",
        help='local dir to sync (current director)')

    push_parser = subparsers.add_parser("push")
    push_parser.set_defaults(func=_sync, pull=False, push=True)
    push_parser.add_argument('-r', '--recursive',
        action='store_true',
        help='descend into directories')
    push_parser.add_argument('pwd', default = os.getcwd(),
        metavar="directory",
        help='local dir to sync (current director)')

    copy_parser = subparsers.add_parser("copy", aliases=['cp'])
    copy_parser.set_defaults(func=_copy)
    copy_parser.add_argument('src_file', help='the source file to copy')
    copy_parser.add_argument('dst_file', help='the destination filename')

    copy_parser = subparsers.add_parser("list", aliases=['ls'])
    copy_parser.set_defaults(func=_list)
    copy_parser.add_argument('path', help='list a remote directory')


    config_parser = subparsers.add_parser("config")
    config_parser.set_defaults(func=_config)
    config_parser.add_argument('name', type=str,
                    help='the name of the shared folder')
    config_parser.add_argument('local_root', type=str,
                    help='the local root for the shared folder')

    list_parser = subparsers.add_parser("show_config")
    list_parser.set_defaults(func=_list_config, pull=True, push=True)

    remove_parser = subparsers.add_parser("remove_config")
    remove_parser.set_defaults(func=_remove_config)
    remove_parser.add_argument('name', type=str,
                    help='the name of the shared folder to remove')

    args = parser.parse_args(argv[1:])

    args.config = os.path.join(args.configdir, "sync.json")

    return args

def main():

    args = parseArgs(sys.argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    try:
        args.func(args)
    except KeyboardInterrupt:
        sys.exit(1)



if __name__ == '__main__':
    main()

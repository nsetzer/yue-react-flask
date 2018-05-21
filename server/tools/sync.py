
import os


def _check(client, root, remote_base, local_base):
    """
    returns 4 lists:
        a list of folders which need to be synced down
        a list of folders which need to be synced up
        a list of files which need to be synced down
        a list of fiels which need to be synced up
    """
    response = client.files_get_path(root, remote_base)

    data = response.json()['result']

    path = data['path']

    directories = set(data['directories'])
    files = {d['name']:(d['mtime'], d['size']) for d in data['files']}

    uld = [] # directories to sync up
    dld = [] # directories to sync down
    ulf = [] # files to sync up
    dlf = [] # files to sync down
    for entry in os.scandir(local_base):
        if entry.is_file():

            local_path = os.path.join(local_base, entry.name)
            st = entry.stat()
            local_size = st.st_size
            local_mtime = int(st.st_mtime)

            if entry.name in files:
                remote_mtime, remote_size = files[entry.name]
                if local_mtime < remote_mtime:
                    #print("remote is newer: %s" % entry.name)
                    dlf.append((entry.name, remote_mtime, remote_size))
                elif local_mtime > remote_mtime:
                    #print("remote is older: %s" % entry.name)
                    ulf.append((entry.name, local_mtime, local_size))
                #else:
                #    #print("files are synced: %s" % entry.name)

                del files[entry.name]
            else:
                #print("no remote match: %s" % entry.name)
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
        print("no local match: %s" % name)
        dlf.append((name, remote_mtime, remote_size))

    for name in directories:
        dld.append(name)

    return dld, uld, dlf, ulf

def _sync(client, root, remote_base, local_base):
    """
    returns 2 lists:
        a list of folders which need to be synced down
        a list of folders which need to be synced up
    """
    dld, uld, dlf, ulf = _check(client, root, remote_base, local_base)

    # download all files marked for download
    for name, mtime, size in dlf:
        print("dlf: %s" % (name,))
        local_path = os.path.join(local_base, name)
        remote_path = os.path.join(remote_base, name)
        response = client.files_get_path(root, remote_path, stream=True)
        with open(local_path, "wb") as wb:
            for chunk in response.stream():
                wb.write(chunk)
        os.utime(local_path, (mtime, mtime))

    # upload all files marked for upload
    for name, mtime, size in ulf:
        print("ulf: %s" % (name,))
        local_path = os.path.join(local_base, name)
        remote_path = os.path.join(remote_base, name)
        with open(local_path, "rb") as rb:
            response = client.files_upload(root, remote_path, rb,
                mtime=mtime)

    return dld, uld
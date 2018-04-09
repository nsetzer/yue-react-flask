import time
import os
import sys
from datetime import datetime, timedelta
from collections import OrderedDict

import bcrypt

def hash_password(password, workfactor=12):
    salt = bcrypt.gensalt(workfactor)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed

def check_password_hash(hash, password):
    return bcrypt.checkpw(password.encode("utf-8"), hash)

def parse_iso_format(dt_str):
    """
    parse a datestring into a datetime object
    as returned from datetime.datetime.now().isoformat()
    or in javascript: new Date().toISOString();
    """
    dt, _, us = dt_str.partition(".")
    dt = datetime.strptime(dt.replace('T', ' '), "%Y-%m-%d %H:%M:%S")
    us = us.rstrip("Z")
    if us:
        us = int(us.rstrip("Z"), 10)
        dt += timedelta(microseconds=us)
    return dt

def format_date(unixTime):
    """ format epoch time stamp as string """
    return time.strftime("%Y/%m/%d %H:%M", time.gmtime(unixTime))

def format_time(t):
    """ format seconds as mm:ss """
    m, s = divmod(t, 60)
    if m > 59:
        h, m = divmod(m, 60)
        return "%d:%02d:%02d" % (h, m, s)
    else:
        return "%d:%02d" % (m, s)

def format_delta(t):
    """ format seconds as days:hh:mm:ss"""
    m, s = divmod(t, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        if h > 23:
            d, h = divmod(h, 24)
            return "%d:%02d:%02d:%02d" % (d, h, m, s)
        return "%d:%02d:%02d" % (h, m, s)
    return "%d:%02d" % (m, s)

byte_labels = ['B', 'KB', 'MB', 'GB']
def format_bytes(b):
    kb = 1024
    for label in byte_labels:
        if b < kb:
            if label == "B":
                return "%d %s" % (b, label)
            if label == "KB":
                if b < 10:
                    return "%.2f %s" % (b, label)
                else:
                    return "%d %s" % (b, label)
            else:
                return "%.2f %s" % (b, label)
        b /= kb
    return "%d%s" % (b, byte_labels[-1])

def days_elapsed(epochtime):
    t1 = datetime.utcfromtimestamp(epochtime)
    delta = datetime.now() - t1
    return delta.days

def string_escape(string):
    """escape special characters in a string for use in search"""
    return string.replace("\\", "\\\\").replace("\"", "\\\"")

def string_quote(string):
    """quote a string for use in search"""
    return "\"" + string.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

def stripIllegalChars(x):
    return ''.join([c for c in x if c not in "<>:\"/\\|?*"])

def pathCorrectCase(path):
    """
        return a normalized file path to the given path.
        Fixes any potential case errors.
    """

    if os.path.exists(path):
        return path

    parts = path.replace("\\", "/").split('/');

    if parts[0] == '~':
        newpath = os.path.expanduser('~')
    elif parts[0] == ".":
        newpath = os.getcwd()
    else:
        newpath = '/'+parts[0]

    for i in range(1,len(parts)):

        if parts[i] == "." or parts[i] == "":
            # a dot is the same as the current directory
            # newpath does not need to be changed
            continue
        elif parts[i] == "..":
            # change to the parent directory
            if newpath !="/":
                newpath = os.path.split(newpath)[0]
            continue

        # test that the given part is a valid file or folder

        testpath = os.path.join(newpath,parts[i])

        if os.path.exists(testpath):
            newpath = testpath;
        else:
            # scan the directory for files with the
            # same name, ignoring case.
            temp = parts[i].lower();
            for item in os.listdir(newpath):
                if item.lower() == temp:
                    newpath = os.path.join(newpath,item)
                    break;
            else:
                raise Exception('Path `%s/%s` not found'%(newpath,temp))

    return newpath

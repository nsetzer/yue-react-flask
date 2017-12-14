import time
import os
import sys
from datetime import datetime
from collections import OrderedDict

try:
    from functools import lru_cache
except:
    def lru_cache(maxsize=128):
        def lru_cache_decorator(func):
            cache = OrderedDict()

            def lru_cache_wrapper(*args):
                if args in cache:
                    return cache[args]
                result = func(*args)
                cache[args] = result
                while len(cache) > maxsize:
                    del cache[cache.keys()[0]]
                return result
            return lru_cache_wrapper
        return lru_cache_decorator

def parse_iso_format(dt_str):
    """
    as returned from datetime.datetime.now().isoformat()
    or in javascript: new Date().toISOString();
    """
    dt, _, us = dt_str.partition(".")
    dt = datetime.strptime(dt.replace('T', ' '), "%Y-%m-%d %H:%M:%S")
    us = us.rstrip("Z")
    if us:
        us = int(us.rstrip("Z"), 10)
        dt += datetime.timedelta(microseconds=us)
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

def format_mode_part(mode):
    s = ""
    s += "r" if 0x4 & mode else "-"
    s += "w" if 0x2 & mode else "-"
    s += "x" if 0x1 & mode else "-"
    return s

def format_mode(mode):
    """ format unix permissions as string
    e.g. octal 0o755 to rwxr-xr-x
    """
    if isinstance(mode, int):
        u = format_mode_part(mode >> 6)  # user
        g = format_mode_part(mode >> 3)  # group
        o = format_mode_part(mode)      # other
        return u + g + o
    return ""

def string_escape(string):
    """escape special characters in a string for use in search"""
    return string.replace("\\", "\\\\").replace("\"", "\\\"")

def string_quote(string):
    """quote a string for use in search"""
    return "\"" + string.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

def stripIllegalChars(x):
    return ''.join([c for c in x if c not in "<>:\"/\\|?*"])


#! python $this

import os
import sys
import string

if sys.platform == "win32":
    from ctypes import windll

    def get_drives():
        drives = []
        #value = windll.kernel32.SetErrorMode(0)
        windll.kernel32.SetErrorMode(1)
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(letter)
            bitmask >>= 1
        result = []
        for drive in [d + ":\\" for d in drives]:
            try:
                os.stat(drive)
                result.append(drive)
            except OSError as e:
                pass
        return result

else:
    def get_drives():
        return ["/",]

if __name__ == '__main__':
    sys.stdout.write("%s\n" % get_drives())
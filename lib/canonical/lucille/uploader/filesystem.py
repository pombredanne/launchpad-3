# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import datetime
import glob
import os
import stat
from zope.security.interfaces import Unauthorized
from zope.server.interfaces.ftp import IFileSystem
from zope.interface import implements


class UploadFileSystem:

    implements(IFileSystem)

    def __init__(self, rootpath):
        self.rootpath = rootpath

    def _full(self, path):
        """Returns the full path name (i.e. rootpath + path)"""
        return os.path.join(self.rootpath, path)

    def _sanitize(self, path):
        if path.startswith('/'):
            path = path[1:]
        path = os.path.normpath(path)
        if '/' in path:
            raise OSError("No access to anything outside CWD:", path)
        else:
            return path

    def type(self, path):
        """Return the file type at path

        The 'type' command returns 'f' for a file, 'd' for a directory and
        None if there is no file.
        """
        path = self._sanitize(path)
        full_path = self._full(path)
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                return 'd'
            elif os.path.isfile(full_path):
                return 'f'
    
    def names(self, path, filter=None):
        """Return a sequence of the names in a directory

        If the filter is not None, include only those names for which
        the filter returns a true value.
        """
        path = self._sanitize(path)
        if path != ".":
            return []
        glob_files = glob.glob(os.path.join(self.rootpath, "*"))
        prefix = "%s/" % self.rootpath
        files = []
        for filename in glob_files:
            if os.path.isfile(filename):
                filename = filename.replace(prefix, "")
                if not filter or filter(filename):
                    files += [filename]
        return files

    def ls(self, path, filter=None):
        """Return a sequence of information objects."""
        path = self._sanitize(path)
        if path != ".":
            return []
        glob_files = glob.glob(os.path.join(self.rootpath, "*"))
        prefix = "%s/" % self.rootpath
        infos = []
        for filename in glob_files:
            if os.path.isfile(filename):
                filename = filename.replace(prefix, "")
                if filter is None or filter(filename):
                    infos.append(self.lsinfo(filename))
        return infos

    def readfile(self, path, outstream, start=0, end=None):
        """Outputs the file at path to a stream.

        Not allowed - see upload.txt.
        """
        raise Unauthorized

    def lsinfo(self, path):
        """Return information for a unix-style ls listing for the path

        See zope3's interfaces/ftp.py:IFileSystem for details of the
        dictionary's content.
        """
        path = self._sanitize(path)
        full_path = self._full(path)
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                raise OSError("Is a directory:", path)
        else:
            raise OSError("Not exists:", path)
        info = {"type": 'f',
                "owner_name": "upload",
                "group_name": "upload",
                "nlinks": 1,
                "name": path}
        s = os.stat(full_path)
        info["owner_readable"] = bool(s[stat.ST_MODE] & stat.S_IRUSR)
        info["owner_writable"] = bool(s[stat.ST_MODE] & stat.S_IWUSR)
        info["owner_executable"] = bool(s[stat.ST_MODE] & stat.S_IXUSR)
        info["group_readable"] = bool(s[stat.ST_MODE] & stat.S_IRGRP)
        info["group_writable"] = bool(s[stat.ST_MODE] & stat.S_IWGRP)
        info["group_executable"] = bool(s[stat.ST_MODE] & stat.S_IXGRP)
        info["other_readable"] = bool(s[stat.ST_MODE] & stat.S_IROTH)
        info["other_writable"] = bool(s[stat.ST_MODE] & stat.S_IWOTH)
        info["other_executable"] = bool(s[stat.ST_MODE] & stat.S_IXOTH)
        info["mtime"] = datetime.datetime.fromtimestamp(self.mtime(path)) 
        info["size"] = self.size(path)
        return info

    def mtime(self, path):
        """Return the modification time for the file"""
        path = self._sanitize(path)
        full_path = self._full(path)
        if os.path.exists(full_path):
            return os.path.getmtime(full_path)

    def size(self, path):
        """Return the size of the file at path"""
        path = self._sanitize(path)
        full_path = self._full(path)
        if os.path.exists(full_path):
            return os.path.getsize(full_path)

    def mkdir(self, path):
        """Create a directory.

        Not Implemented - see upload.txt.
        """
        path = self._sanitize(path)

    def remove(self, path):
        """Remove a file."""
        path = self._sanitize(path)
        full_path = self._full(path)
        if os.path.exists(full_path):
            if os.path.isfile(full_path):
                os.unlink(full_path)
            elif os.path.isdir(full_path):
                raise OSError("Is a directory:", path)
        else:
            raise OSError("Not exists:", path)

    def rmdir(self, path):
        """Remove a directory.

        Not Implemented - see upload.txt.
        """
        path = self._sanitize(path)

    def rename(self, old, new):
        """Rename a file."""
        old = self._sanitize(old)
        new = self._sanitize(new)
        full_old = self._full(old)
        full_new = self._full(new)

        if os.path.isdir(full_new):
            raise OSError("Is a directory:", new)

        if os.path.exists(full_old):
            if os.path.isfile(full_old):
                os.rename(full_old, full_new)
            elif os.path.isdir(full_old):
                raise OSError("Is a directory:", old)
        else:
            raise OSError("Not exists:", old)

    def writefile(self, path, instream, start=None, end=None, append=False):
        """Write data to a file.

        See zope3's interfaces/ftp.py:IFileSystem for details of the
        handling of the various arguments.
        """
        path = self._sanitize(path)
        full_path = self._full(path)
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                raise OSError("Is a directory:", path)
        if start and start < 0:
            raise ValueError("Negative start argument:", start)
        if end and end < 0:
            raise ValueError("Negative end argument:", end)
        if start and end and end <= start:
            return
        if append:
            open_flag = 'a'
        elif start or end:
            open_flag = "r+"
            if not os.path.exists(full_path):
                open(full_path, 'w')

        else:
            open_flag = 'w'
        outstream = open(full_path, open_flag)
        if start:
            outstream.seek(start)
        chunk = instream.read()
        while chunk:
            outstream.write(chunk)
            chunk = instream.read()
        if not end:
            outstream.truncate()
        instream.close()
        outstream.close()

    def writable(self, path):
        """Return boolean indicating whether a file at path is writable."""
        path = self._sanitize(path)
        full_path = self._full(path)
        if os.path.exists(full_path):
            if os.path.isfile(full_path):
                return True
            elif os.path.isdir(full_path):
                return False
        else:
            return True


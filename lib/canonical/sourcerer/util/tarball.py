#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: bdaad292-b07c-4e93-b549-35660b067402
"""Unpack tar files.

This module contains a function to unpack a tar file into a directory.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os
import bz2
import gzip

class TarballUnpackError(Exception): pass


def unpack(tarfile, path):
    """Unpack the tar file into the directory.

    If the tar file contains a single directory, the contents of that
    directory are placed in the directory otherwise the file is unpacked
    under it.  This is roughly consistent with dpkg-dev's behaviour.
    """
    if not os.path.isdir(path):
        if os.path.exists(path):
            raise TarballUnpackError, "Path is not a directory"
        else:
            os.makedirs(path)

    if tarfile.endswith("gz"):
        options = "xzf"
    elif tarfile.endswith("bz2"):
        options = "xjf"
    elif tarfile.endswith("Z"):
        options = "xZf"
    else:
        options = "xf"

    tmppath = os.path.join(path, ",,unpack." + os.path.basename(path))
    os.mkdir(tmppath)

    cmd = ( "tar", options, tarfile, "-C", tmppath )
    ret = os.spawnvp(os.P_WAIT, cmd[0], cmd)
    if ret != 0:
        raise TarballUnpackError, "tar sub-process failed"

    entries = os.listdir(tmppath)
    if len(entries) == 1 and os.path.isdir(os.path.join(tmppath, entries[0])):
        entry = entries[0]
        for subentry in os.listdir(os.path.join(tmppath, entries[0])):
            os.rename(os.path.join(tmppath, entry, subentry),
                      os.path.join(path, subentry))

        os.rmdir(os.path.join(tmppath, entry))
    else:
        for entry in entries:
            os.rename(os.path.join(tmppath, entry), os.path.join(path, entry))

    os.rmdir(tmppath)

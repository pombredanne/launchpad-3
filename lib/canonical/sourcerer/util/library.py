#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: e4c39bda-632b-4cd1-bc17-1d02ff406618
"""Manage temporary directories.

This module contains a class that implements a form of managed temporary
directories allowing us to work on things without clashing with user
filenames.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os
import shutil

import log


class LibraryError(Exception): pass

class Library(object):
    """Library of directories.

    This class manages a library of temporary directories that can be
    indexeed by any arbitrary string.  A directory must be created
    with the create() function and populated however you wish.
    """

    i = 0

    def __init__(self, log_parent=None):
        i = Library.i = Library.i + 1
        self.log = log.get_logger("Library.%d" % i, log_parent)
        self.libdir = os.path.abspath(",,library.%d.%d" % (os.getpid(), i))
        self.library = {}

        if not os.path.isdir(self.libdir):
            self.log.info("Creating library directory '%s'", self.libdir)
            os.makedirs(self.libdir)

    def __del__(self):
        if os.path.isdir(self.libdir):
            self.log.info("Removing library directory")
            shutil.rmtree(self.libdir)

    def contains(self, objname):
        """Return whether the library contains the directory."""
        return str(objname) in self.library

    __contains__ = contains

    def create(self, objname):
        """Create the directory and return its path."""
        if self.contains(objname):
            raise LibraryError, "Directory already in library: " + objname

        dirname = objname.replace("/", ",,")
        self.library[objname] = os.path.join(self.libdir, dirname)
        if not os.path.isdir(self.library[objname]):
            self.log.info("Creating directory '%s'", objname)
            os.makedirs(self.library[objname])

        return self.library[objname]

    def get(self, objname):
        """Return the path to the directory."""
        if not self.contains(objname):
            raise LibraryError, "Directory not in library: " + objname

        return self.library[objname]

    def getPath(self, objname):
        """Return the path to the directory."""
        return self.get(objname)

    def remove(self, objname):
        """Remove the directory from the library."""
        if not self.contains(objname):
            raise LibraryError, "Directory not in library: " + objname

        self.log.info("Removing directory '%s'", objname)
        path = self.getPath(objname)
        shutil.rmtree(path)
        del(self.library[objname])

    def clone(self, objname, newpath):
        """Create an clone of the directory somewhere else.

        A clone is an identical copy of the directory and will include
        any special metadata files or directories that copy() will
        normally omit.
        """
        self.log.info("Cloning '%s' into '%s'", objname, newpath)
        path = self.getPath(objname)

        for dirpath, dirnames, filenames in os.walk(path):
            subdir = dirpath[len(path):]
            while subdir[:1] == "/":
                subdir = subdir[1:]

            destdir = os.path.join(newpath, subdir)
            if not os.path.isdir(destdir):
                os.makedirs(destdir)

            for filename in filenames:
                srcpath = os.path.join(dirpath, filename)
                dstpath = os.path.join(destdir, filename)
                if os.path.islink(srcpath):
                    linkdest = os.readlink(srcpath)
                    os.symlink(linkdest, dstpath)
                else:
                    shutil.copy2(srcpath, dstpath)

    def copy(self, objname, newpath):
        """Create an copy of the directory somewhere else."""
        return self.clone(objname, newpath)

    def cloneFrom(self, library, objname, newname):
        """Create a clone of an directory from another library in this one.

        This adds an directory to the current library by calling clone()
        on it from its source library.
        """
        path = self.create(newname)
        try:
            library.clone(objname, path)
        except:
            self.remove(newname)
            raise

        return path

    def copyFrom(self, library, objname, newname):
        """Create a copy of an directory from another library in this one.

        This adds an directory to the current library by calling copy()
        on it from its source library.
        """
        path = self.create(newname)
        try:
            library.copy(objname, path)
        except:
            self.remove(newname)
            raise

        return path

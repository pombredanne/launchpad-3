#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: 95b2c164-ddad-4d98-b19a-201d04451622
"""Parse Debian source control (dsc) files.

This module contains a subclass of the generic ControlFile class (in
deb.controlfile) which handles the extra functionality of dsc files.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import re

from controlfile import ControlFile
from version import Version


# Regular expressions make validating things easy
valid_source = re.compile(r'^[a-z0-9][a-z0-9+.-]*$')
valid_filename = re.compile(r'^[A-Za-z0-9][A-Za-z0-9+:.,_=-]*$')


class SourceError(Exception): pass
class SourceControlError(SourceError): pass
class SourceFileError(SourceError): pass

class SourceControl(ControlFile):
    """Debian source control (dsc) file.

    Properties:
      dsc_format  Format of the dsc file
      source      Name of the source package
      version     Version information (as a Version object)
      files       List of accompanying files (as SourceFile objects)
      tar         Accompanying tar file
      diff        Accompanying diff file (if any)
    """

    def __init__(self, filename=None, fileobj=None):
        super(SourceControl, self).__init__()

        self.dsc_format = 1.0
        self.source = None
        self.version = None
        self.files = []
        self.tar = None
        self.diff = None

        if fileobj is not None:
            self.parse(fileobj)
        elif filename is not None:
            self.open(filename)

    def parse(self, file):
        """Parse source control (dsc) file.

        Parses the opened source control (dsc) file given, validates it
        and stores the most important information in the object.  The
        rest of the fields can still be accessed through the para
        member.
        """
        super(SourceControl, self).parse(file, signed=True)

        if "Format" in self.para:
            try:
                self.dsc_format = float(self.para["Format"])
                if int(self.dsc_format) != 1:
                    raise SourceControlError, \
                          "Unhandled format " + str(self.dsc_format)
            except ValueError:
                raise SourceControlError, "Bad Format field format"

        if "Source" in self.para:
            self.source = self.para["Source"]
            if not valid_source.search(self.source):
                raise SourceControlError, "Illegal package name"
        else:
            raise SourceControlError, "Missing mandatory Source field"

        if "Version" in self.para:
            self.version = Version(self.para["Version"])
        else:
            raise SourceControlError, "Missing mandatory Version field"

        if "Files" in self.para:
            files = self.para["Files"].strip("\n").split("\n")
            for f in files:
                try:
                    (md5sum, size, name) = f.split(None, 2)
                except ValueError:
                    raise SourceControlError, "Illegal line in Files field"

                sf = SourceFile(name, size, md5sum)
                if name.endswith(".tar.gz"):
                    if self.tar:
                        raise SourceControlError, \
                              "Duplicate tar file in Files field"
                    self.tar = sf
                elif name.endswith(".diff.gz"):
                    if self.diff:
                        raise SourceControlError, \
                              "Duplicate diff file in Files field"
                    self.diff = sf
                self.files.append(sf)

            if not self.tar:
                raise SourceControlError, "Missing tar file in Files field"
        else:
            raise SourceControlError, "Missing mandatory Files field"


class SourceFile(object):
    """File belonging to a Debian source package.

    Properties:
      name        Relative filename of the file
      size        Expected size of the file
      md5sum      Expected md5sum of the file
    """

    def __init__(self, name, size, md5sum):
        if not valid_filename.search(name):
            raise SourceFileError, "Illegal filename"

        self.name = name
        self.size = size
        self.md5sum = md5sum

    def __str__(self):
        """Return the name of the file."""
        return self.name

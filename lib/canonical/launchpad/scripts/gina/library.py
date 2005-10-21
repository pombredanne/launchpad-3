# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Library access methods to gina."""

import os
import sha

from zope.component import getUtility

from canonical.launchpad.interfaces import ILibraryFileAliasSet
from canonical.launchpad.database import LibraryFileContent
from canonical.launchpad.scripts import execute_zcml_for_scripts


execute_zcml_for_scripts()
librarian = getUtility(ILibraryFileAliasSet)


def _libType(fname):
    if fname.endswith(".dsc"):
        return "text/x-debian-source-package"
    if fname.endswith(".deb"):
        return "application/x-debian-package"
    if fname.endswith(".udeb"):
        return "application/x-micro-debian-package"
    if fname.endswith(".diff.gz"):
        return "application/gzipped-patch"
    if fname.endswith(".tar.gz"):
        return "application/gzipped-tar"
    return "application/octet-stream"


def getLibraryAlias(root, filename):
    global librarian
    if librarian is None:
        return None
    fname = os.path.join(root, filename)
    fobj = open(fname, "rb")
    size = os.stat(fname).st_size
    alias = librarian.create(filename, size, fobj,
                             contentType=_libType(filename))
    fobj.close()
    return alias


def checkLibraryForFile(path, filename):
    fullpath = os.path.join(path, filename)
    assert os.path.exists(fullpath)
    digester = sha.sha()
    openfile = open(fullpath, "r")
    for chunk in iter(lambda: openfile.read(1024*4), ''):
        digester.update(chunk)
    digest = digester.hexdigest()
    openfile.close()
    return LibraryFileContent.selectOneBy(sha1=digest)


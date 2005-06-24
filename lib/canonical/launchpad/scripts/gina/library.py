# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Library access methods to gina."""

import os, sha

from canonical.librarian.client import LibrarianClient
from zope.component import getUtility

from canonical.launchpad.interfaces import ILibraryFileAliasSet
from canonical.launchpad.scripts import execute_zcml_for_scripts


execute_zcml_for_scripts()
librarian = getUtility(ILibraryFileAliasSet).create

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
    fname = "%s/%s"%(root,filename)
    fobj = open( fname, "rb" )
    size = os.stat(fname).st_size
    alias = librarian(filename, size, fobj,
                      contentType=_libType(filename))
                                 
    fobj.close()
    return alias


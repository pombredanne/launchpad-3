#!/usr/bin/python

"""Copyright Canonical Limited 2005
 Author: Matt Zimmerman <matt.zimmerman@canonical.com>
     based on upload2librarian.py by:
         Daniel Silverstone <daniel.silverstone@canonical.com>
         Celso Providelo <celso.providelo@canonical.com>
 Tool for adding, removing and replacing buildd chroots
"""

import sys
import os
import _pythonpath

from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.librarian.interfaces import ILibrarianClient

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.database.distroarchrelease import PocketChroot


def addFile(filepath, client):
    """Add a file to librarian."""
    # verify filepath
    if not filepath:
        print 'Filepath is required'
        return

    # open given file
    try:
        fd = open(filepath)
    except IOError:
        print 'Could not open:', filepath
        return

    # XXX: cprov 20050613
    # os.fstat(fd) presents an strange behavior
    flen = os.stat(filepath).st_size
    filename = os.path.basename(filepath)
    ftype = filenameToContentType(filename)

    return client.addFile(filename, flen, fd, contentType=ftype)


def addChroot(replace, where, architecture, filepath):
    ubuntu = getUtility(IDistributionSet)['ubuntu']
    release, pocket = ubuntu.getDistroReleaseAndPocket(where)
    dar = release[architecture]

    client = getUtility(ILibrarianClient)
    alias = addFile(filepath, client)

    existing = PocketChroot.selectOneBy(distroarchreleaseID=dar.id,
                                        pocket=pocket)

    if existing and not replace:
        print >> sys.stderr, "Use 'update' to modify existent chroots."
        sys.exit(1)

    if replace:
        if existing is not None:
            existing.chroot = alias
        else:
            print >> sys.stderr, "No existing chroot found to update"
            sys.exit(1)
    else:
        PocketChroot(distroarchrelease=dar, pocket=pocket, chroot=alias)


if __name__ == '__main__':
    parser = OptionParser(usage='%prog {add|update} <distrorelease> '
                                '<arch> <tarfile>')

    (options, args) = parser.parse_args()

    if not args:
        parser.print_usage(file=sys.stderr)
        sys.exit(1)

    tm = initZopeless(dbuser="fiera")
    execute_zcml_for_scripts()

    command = args.pop(0).lower()

    if command == 'add':
        addChroot(False, *args)
    elif command == 'update':
        addChroot(True, *args)
    else:
        parser.print_usage(file=sys.stderr)
        sys.exit(1)

    tm.commit()

    print "Success."

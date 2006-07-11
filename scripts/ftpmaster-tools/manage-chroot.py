#!/usr/bin/python

"""Copyright Canonical Limited 2005
 Author: Matt Zimmerman <matt.zimmerman@canonical.com>
     based on upload2librarian.py by:
         Daniel Silverstone <daniel.silverstone@canonical.com>
         Celso Providelo <celso.providelo@canonical.com>
 Tool for adding, removing and replacing buildd chroots
"""

import _pythonpath
from optparse import OptionParser
import os
import sys

from zope.component import getUtility

from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces import (
    IDistributionSet, NotFoundError, ILibraryFileAliasSet)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)

from canonical.librarian.interfaces import (
    ILibrarianClient, UploadFailed)
from canonical.lp import initZopeless

def main():
    parser = OptionParser()
    logger_options(parser)

    (options, args) = parser.parse_args()

    log = logger(options, "manage-chroot")

    try:
        where = args[0]
        architecture = args[1]
        filepath = args[2]
    except ValueError:
        log.error('manage-chroot.py <distrorelease> <arch> <tarfile>')
        return 1

    ztm = initZopeless(dbuser="fiera")
    execute_zcml_for_scripts()

    try:
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        release, pocket = ubuntu.getDistroReleaseAndPocket(where)
        dar = release[architecture]
    except NotFoundError, info:
        log.error("Not found: %s" % info)
        return 1

    try:
        fd = open(filepath)
    except IOError:
        log.error('Could not open: %s' % filepath)
        return 1

    # XXX: cprov 20050613
    # os.fstat(fd) presents an strange behavior
    flen = os.stat(filepath).st_size
    filename = os.path.basename(filepath)
    ftype = filenameToContentType(filename)


    try:
        alias_id  = getUtility(ILibrarianClient).addFile(
            filename, flen, fd, contentType=ftype)
    except UploadFailed, info:
        log.error("Librarian upload failed: %s" % info)
        ztm.abort()
        return 1

    alias = getUtility(ILibraryFileAliasSet)[alias_id]
    dar.addOrUpdateChroot(pocket, alias)
    ztm.commit()

    log.info("Success.")

    return 0

if __name__ == '__main__':
    sys.exit(main())

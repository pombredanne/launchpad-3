#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
"""Create a rebuild archive.

The command line options supported are as follows:

    -c c | --component c : component from which to copy source packages.
                         One of: main, restricted, universe, multiverse,
                         partner.
    -d d | --distribution d : the distribution for which the rebuild archive
                         is to be created.
    -r n | --rebuildarchive n : the name of the rebuild archive to be created.
    -s s | --suite s   : the suite (distribution series + publishing pocket)
                         for which the rebuild archive is to be created.
    -t t | --text t    : the reason for the rebuild
    -u u | --user u    : the user creating the rebuild archive.
"""


import sys

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.create_rebuild import RebuildArchiveCreator

if __name__ == '__main__':
    from canonical.launchpad.scripts.ftpmaster import PackageLocationError
    script = RebuildArchiveCreator(
        'start-rebuild', dbuser=config.uploader.dbuser)
    try:
        script.lock_and_run()
    except PackageLocationError, e:
        print str(e)
        sys.exit(1)

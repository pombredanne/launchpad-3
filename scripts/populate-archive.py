#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
"""Create a copy archive and populate it with packages.

    Please note: the destination copy archive must not exist yet. Otherwise
    the script will abort with an error.
"""


import sys

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.populate_archive import ArchivePopulator
from canonical.launchpad.scripts.ftpmaster import (
    PackageLocationError, SoyuzScriptError)

if __name__ == '__main__':
    script = ArchivePopulator(
        'populate-archive', dbuser=config.archivepublisher.dbuser)
    try:
        script.lock_and_run()
    except (SoyuzScriptError, PackageLocationError), e:
        print str(e)
        sys.exit(1)

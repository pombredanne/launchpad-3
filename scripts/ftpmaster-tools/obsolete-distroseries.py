#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

# Stop lint warning about relative import:
# pylint: disable-msg=W0403

"""Obsolete all packages in an obsolete distroseries.

This script will obsolete (schedule for removal) all published packages
in an obsolete distroseries.
"""

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.ftpmaster import ObsoleteDistroseries


if __name__ == '__main__':
    script = ObsoleteDistroseries(
        'obsolete-distroseries', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()


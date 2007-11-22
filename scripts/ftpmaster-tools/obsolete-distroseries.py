#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Obsolete (schedule for removal) all the packages in an obsolete
distroseries.
"""

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.ftpmaster import ObsoleteDistroseries


if __name__ == '__main__':
    script = ObsoleteDistroseries(
        'obsolete-distroseries', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()


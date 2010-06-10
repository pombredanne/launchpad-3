#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Stop lint warning about relative import:
# pylint: disable-msg=W0403

"""Obsolete all packages in an obsolete distroseries.

This script will obsolete (schedule for removal) all published packages
in an obsolete distroseries.
"""

import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.ftpmaster import ObsoleteDistroseries


if __name__ == '__main__':
    script = ObsoleteDistroseries(
        'obsolete-distroseries', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()


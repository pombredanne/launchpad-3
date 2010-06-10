#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

"""
Cron job to run daily to check all of the BugWatches
"""

import _pythonpath

from canonical.config import config
from lp.bugs.scripts.checkwatches import CheckWatchesCronScript

if __name__ == '__main__':
    script = CheckWatchesCronScript(
        "checkwatches", dbuser=config.checkwatches.dbuser)
    script.lock_and_run()

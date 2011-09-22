#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Stop pylint complaining about the _pythonpath relative import.
# pylint: disable-msg=W0403

"""Queue/Accepted processor

Given a distribution to run on, obtains all the queue items for the
distribution and then gets on and deals with any accepted items, preparing
them for publishing as appropriate.
"""

import _pythonpath

from canonical.config import config
from canonical.database.sqlbase import ISOLATION_LEVEL_READ_COMMITTED
from lp.soyuz.scripts.processaccepted import ProcessAccepted


if __name__ == '__main__':
    script = ProcessAccepted(
        "process-accepted", dbuser='process_accepted')
    script.lock_and_run(isolation=ISOLATION_LEVEL_READ_COMMITTED)


#!/usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Queue/Accepted processor

Given a distribution to run on, obtains all the queue items for the
distribution and then gets on and deals with any accepted items, preparing
them for publishing as appropriate.
"""

import _pythonpath

import sys
from optparse import OptionParser

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import ISOLATION_LEVEL_READ_COMMITTED
from lp.soyuz.interfaces.queue import PackageUploadStatus
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from lp.soyuz.scripts.processaccepted import close_bugs
from canonical.lp import initZopeless

from contrib.glock import GlobalLock


if __name__ == '__main__':
    script = ProcessAccepted(
        "process-accepted", dbuser=config.uploadqueue.dbuser,
        isolation=ISOLATION_LEVEL_READ_COMMITTED)
    script.lock_and_run()


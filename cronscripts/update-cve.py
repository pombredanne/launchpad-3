#!/usr/bin/python2.4

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""A cron script that fetches the latest database of CVE details and ensures
that all of the known CVE's are fully registered in Launchpad."""

__metaclass__ = type

import _pythonpath

from canonical.config import config
from lp.bugs.scripts.cveimport import CVEUpdater


if __name__ == '__main__':
    script = CVEUpdater("updatecve", config.cveupdater.dbuser)
    script.lock_and_run()


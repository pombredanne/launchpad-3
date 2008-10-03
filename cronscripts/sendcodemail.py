#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Send code mail.

This script sends out all the mail jobs that are pending.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.launchpad.interfaces import ICodeMailJobSource
from canonical.launchpad.scripts.base import LaunchpadCronScript


class RunCodeMailJobs(LaunchpadCronScript):
    """Run pending code mail jobs."""

    def main(self):
        getUtility(ICodeMailJobSource).runAll()


if __name__ == '__main__':
    script = RunCodeMailJobs('sendcodemail').run()

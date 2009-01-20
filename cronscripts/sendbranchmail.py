#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Send branch mail.

This script sends out all the mail jobs that are pending.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from canonical.codehosting.jobs import JobRunner
from canonical.launchpad.interfaces.branch import IRevisionMailJobSource
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunRevisionMailJobs(LaunchpadCronScript):
    """Run pending branch mail jobs."""

    def main(self):
        globalErrorUtility.configure('sendbranchmail')
        runner = JobRunner.fromReady(getUtility(IRevisionMailJobSource))
        runner.runAll()
        print 'Ran %d RevisionMailJobs.' % len(runner.completed_jobs)


if __name__ == '__main__':
    script = RunRevisionMailJobs('sendcodemail', config.branchscanner.dbuser)
    script.lock_and_run()

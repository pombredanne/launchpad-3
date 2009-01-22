#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Send branch mail.

This script sends out all the mail jobs that are pending.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from canonical.codehosting.branchfs import get_scanner_server
from canonical.codehosting.jobs import JobRunner
from canonical.launchpad.interfaces.branchmergeproposal import (
    IReviewDiffJobSource,)
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunReviewDiffJobs(LaunchpadCronScript):
    """Run pending branch mail jobs."""

    def main(self):
        globalErrorUtility.configure('diff_bmps')
        runner = JobRunner.fromReady(getUtility(IReviewDiffJobSource))
        server = get_scanner_server()
        server.setUp()
        try:
            runner.runAll()
        finally:
            server.tearDown()
        print 'Ran %d ReviewDiffJobs.' % len(runner.completed_jobs)


if __name__ == '__main__':
    script = RunReviewDiffJobs('sendcodemail', config.diff_bmps.dbuser)
    script.lock_and_run()

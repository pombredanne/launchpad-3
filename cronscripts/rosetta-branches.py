#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Process branches with translation to import.

This script processes code branches that have new translations imports
pending.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from lp.codehosting.vfs.branchfs import get_scanner_server
from lp.services.job.runner import JobRunner
from lp.code.interfaces.branchjob import IRosettaUploadJobSource
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunRosettaBranchJobs(LaunchpadCronScript):
    """Run pending branch translations jobs."""

    def main(self):
        globalErrorUtility.configure('rosettabranches')
        runner = JobRunner.fromReady(getUtility(IRosettaUploadJobSource))
        server = get_scanner_server()
        server.setUp()
        try:
            runner.runAll()
        finally:
            server.tearDown()
        self.logger.info('Ran %d RosettaBranchJobs.',
                         len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunRosettaBranchJobs('rosettabranches',
                                  config.rosettabranches.dbuser)
    script.lock_and_run()

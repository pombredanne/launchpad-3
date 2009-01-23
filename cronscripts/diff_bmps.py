#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Handle new BranchMergeProposals.

This script generates a diff for the merge proposal if needed, then notifies
all interested parties about the merge proposal.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from canonical.codehosting.branchfs import get_scanner_server
from canonical.codehosting.jobs import JobRunner
from canonical.launchpad.interfaces.branchmergeproposal import (
    IMergeProposalCreatedJobSource,)
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunMergeProposalCreatedJobs(LaunchpadCronScript):
    """Run merge proposal creation jobs."""

    def main(self):
        globalErrorUtility.configure('diff_bmps')
        job_source = getUtility(IMergeProposalCreatedJobSource)
        runner = JobRunner.fromReady(job_source)
        server = get_scanner_server()
        server.setUp()
        try:
            runner.runAll()
        finally:
            server.tearDown()
        print 'Ran %d MergeProposalCreatedJobs.' % len(runner.completed_jobs)


if __name__ == '__main__':
    script = RunMergeProposalCreatedJobs(
        'sendcodemail', config.diff_bmps.dbuser)
    script.lock_and_run()

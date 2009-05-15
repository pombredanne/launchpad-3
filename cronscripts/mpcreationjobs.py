#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Handle new BranchMergeProposals.

This script generates a diff for the merge proposal if needed, then notifies
all interested parties about the merge proposal.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from canonical.codehosting.vfs import get_scanner_server
from lp.services.job.runner import JobRunner
from lp.code.interfaces.branchmergeproposal import (
    IMergeProposalCreatedJobSource,)
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunMergeProposalCreatedJobs(LaunchpadCronScript):
    """Run merge proposal creation jobs."""

    def main(self):
        globalErrorUtility.configure('mpcreationjobs')
        job_source = getUtility(IMergeProposalCreatedJobSource)
        runner = JobRunner.fromReady(job_source)
        server = get_scanner_server()
        server.setUp()
        try:
            runner.runAll()
        finally:
            server.tearDown()
        self.logger.info(
            'Ran %d MergeProposalCreatedJobs.', len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunMergeProposalCreatedJobs(
        'mpcreationjobs', config.mpcreationjobs.dbuser)
    script.lock_and_run()

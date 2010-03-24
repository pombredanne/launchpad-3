#!/usr/bin/python2.5
#
# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Handle jobs for BranchMergeProposals.

This script handles all job types for branch merge proposals.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from lp.codehosting.vfs import get_scanner_server
from lp.services.job.runner import JobRunner
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposalJobSource,
    )
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunMergeProposalCreatedJobs(LaunchpadCronScript):
    """Run merge proposal creation jobs."""

    def main(self):
        globalErrorUtility.configure('merge_proposal_jobs')
        job_source = getUtility(IBranchMergeProposalJobSource)
        runner = JobRunner.fromReady(job_source, self.logger)
        server = get_scanner_server()
        server.start_server()
        try:
            runner.runAll()
        finally:
            server.stop_server()
        self.logger.info(
            'Ran %d MergeProposalCreatedJobs.', len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunMergeProposalCreatedJobs(
        'merge-proposal-jobs', config.merge_proposal_email_jobs.dbuser)
    script.lock_and_run()

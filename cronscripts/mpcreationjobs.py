#!/usr/bin/python2.5 -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Handle new BranchMergeProposals.

This script generates a diff for the merge proposal if needed, then notifies
all interested parties about the merge proposal.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from lp.codehosting.vfs import get_ro_server
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
        runner = JobRunner.fromReady(job_source, self.logger)
        server = get_ro_server()
        server.start_server()
        try:
            runner.runAll()
        finally:
            server.stop_server()
        self.logger.info(
            'Ran %d MergeProposalCreatedJobs.', len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunMergeProposalCreatedJobs(
        'mpcreationjobs', config.mpcreationjobs.dbuser)
    script.lock_and_run()

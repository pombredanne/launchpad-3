#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Create BranchMergeProposals from email."""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from lp.services.job.runner import JobRunner
from lp.code.interfaces.branchmergeproposal import (
    ICreateMergeProposalJobSource,)
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunCreateMergeProposalJobs(LaunchpadCronScript):
    """Run create merge proposal jobs."""

    def main(self):
        globalErrorUtility.configure('create_merge_proposals')
        job_source = getUtility(ICreateMergeProposalJobSource)
        runner = JobRunner.fromReady(job_source, self.logger)
        runner.runAll()
        self.logger.info(
            'Ran %d CreateMergeProposalJobs.' % len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunCreateMergeProposalJobs(
        'create_merge_proposals', config.create_merge_proposals.dbuser)
    script.lock_and_run()

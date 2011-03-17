#!/usr/bin/python -S
#
# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Handle jobs for BranchMergeProposals.

This script handles all job types for branch merge proposals.
"""

__metaclass__ = type

import _pythonpath

# The following line is a horrible hack, but unfortunately necessary right now
# to stop import errors from circular imports.
import canonical.launchpad.interfaces
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposalJobSource,
    )
from lp.services.job.runner import JobCronScript, TwistedJobRunner


class RunMergeProposalJobs(JobCronScript):
    """Run all merge proposal jobs."""

    config_name = 'merge_proposal_jobs'
    source_interface = IBranchMergeProposalJobSource

    def __init__(self):
        super(RunMergeProposalJobs, self).__init__(
            runner_class=TwistedJobRunner,
            name='merge-proposal-jobs')


if __name__ == '__main__':
    script = RunMergeProposalJobs()
    script.lock_and_run()

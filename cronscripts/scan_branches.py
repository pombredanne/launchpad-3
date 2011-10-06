#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Scan branches for new revisions."""

__metaclass__ = type

import _pythonpath

from lp.code.interfaces.branchjob import IBranchScanJobSource
from lp.services.job.runner import (
    JobCronScript,
    TwistedJobRunner,
    )


class RunScanBranches(JobCronScript):
    """Run BranchScanJob jobs."""

    config_name = 'branchscanner'
    source_interface = IBranchScanJobSource

    def __init__(self):
        super(RunScanBranches, self).__init__(runner_class=TwistedJobRunner)


if __name__ == '__main__':

    script = RunScanBranches()
    script.lock_and_run()

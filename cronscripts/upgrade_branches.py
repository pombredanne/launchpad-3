#!/usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Upgrade branches to the most recent format."""

__metaclass__ = type

import _pythonpath

from lp.services.job.runner import JobCronScript
from lp.code.interfaces.branchjob import IBranchUpgradeJobSource


class RunUpgradeBranches(JobCronScript):
    """Run UpdatePreviewDiff jobs."""

    config_name = 'upgrade_branches'
    source_interface = IBranchUpgradeJobSource

    def setUp(self):
        return []


if __name__ == '__main__':
    script = RunUpgradeBranches()
    script.lock_and_run()

#!/usr/bin/python2.5
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Calculate bug heat."""

__metaclass__ = type

import _pythonpath

from canonical.launchpad.webapp import errorlog

from lp.services.job.runner import JobCronScript
from lp.bugs.interfaces.bugjob import ICalculateBugHeatJobSource


class RunCalculateBugHeat(JobCronScript):
    """Run BranchScanJob jobs."""

    config_name = 'calculate_bug_heat'
    source_interface = ICalculateBugHeatJobSource

    def main(self):
        errorlog.globalErrorUtility.configure(self.config_name)
        return super(RunCalculateBugHeat, self).main()


if __name__ == '__main__':
    script = RunCalculateBugHeat()
    script.lock_and_run()

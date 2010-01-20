#!/usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Calculate bug heat."""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from lp.services.job.runner import JobRunner
from lp.bugs.interfaces.bugjob import ICalculateBugHeatJobSource
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunCalculateBugHeatJobs(LaunchpadCronScript):
    """Run calculate bug heat jobs."""

    def main(self):
        globalErrorUtility.configure('calculate_bug_heat')
        job_source = getUtility(ICalculateBugHeatJobSource)
        runner = JobRunner.fromReady(job_source, self.logger)
        runner.runAll()
        self.logger.info(
            'Ran %d CalculateBugHeatJobs.' % len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunCalculateBugHeatJobs(
        'calculate_bug_heat', config.calculate_bug_heat.dbuser)
    script.lock_and_run()

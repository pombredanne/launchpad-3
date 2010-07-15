#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Delete from disk branches deleted from the database."""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.webapp.errorlog import globalErrorUtility
from lp.code.interfaces.branchjob import (
    IReclaimBranchSpaceJobSource)
from lp.services.job.runner import JobRunner
from lp.services.scripts.base import LaunchpadCronScript


class RunReclaimBranchSpaceJobs(LaunchpadCronScript):
    """Run merge proposal creation jobs."""

    def main(self):
        globalErrorUtility.configure('reclaimbranchspace')
        job_source = getUtility(IReclaimBranchSpaceJobSource)
        runner = JobRunner.fromReady(job_source, self.logger)
        runner.runAll()
        self.logger.info(
            'Reclaimed space for %s branches.', len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunReclaimBranchSpaceJobs(
        'reclaimbranchspace', config.reclaimbranchspace.dbuser)
    script.lock_and_run()

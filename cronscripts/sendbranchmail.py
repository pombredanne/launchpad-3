#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Send branch mail.

This script sends out all the mail jobs that are pending.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from lp.codehosting.vfs import get_ro_server
from lp.services.job.runner import JobRunner
from lp.code.interfaces.branchjob import (
    IRevisionMailJobSource, IRevisionsAddedJobSource)
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunRevisionMailJobs(LaunchpadCronScript):
    """Run pending branch mail jobs."""

    def main(self):
        globalErrorUtility.configure('sendbranchmail')
        jobs = list(getUtility(IRevisionMailJobSource).iterReady())
        jobs.extend(getUtility(IRevisionsAddedJobSource).iterReady())
        runner = JobRunner(jobs, self.logger)
        server = get_ro_server()
        server.start_server()
        try:
            runner.runAll()
        finally:
            server.stop_server()
        self.logger.info(
            'Ran %d RevisionMailJobs.' % len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunRevisionMailJobs(
        'sendbranchmail', config.sendbranchmail.dbuser)
    script.lock_and_run()

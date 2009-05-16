#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Send branch mail.

This script sends out all the mail jobs that are pending.
"""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from canonical.codehosting.vfs import get_scanner_server
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
        runner = JobRunner(jobs)
        server = get_scanner_server()
        server.setUp()
        try:
            runner.runAll()
        finally:
            server.tearDown()
        self.logger.info(
            'Ran %d RevisionMailJobs.' % len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunRevisionMailJobs(
        'sendbranchmail', config.sendbranchmail.dbuser)
    script.lock_and_run()

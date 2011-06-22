#!/usr/bin/python -S
#
# Copyright 2008-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Send branch mail.

This script sends out all the mail jobs that are pending.
"""

__metaclass__ = type


from contextlib import contextmanager
from itertools import chain
import logging

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from lp.codehosting.vfs import get_ro_server
from lp.services.job.runner import (
    BaseRunnableJobSource,
    JobRunner,
    )
from lp.code.interfaces.branchjob import (
    IRevisionMailJobSource,
    IRevisionsAddedJobSource,
    )
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class BranchMailJobSource(BaseRunnableJobSource):

    @staticmethod
    def iterReady():
        return chain(
            getUtility(IRevisionMailJobSource).iterReady(),
            getUtility(IRevisionsAddedJobSource).iterReady())

    @staticmethod
    def contextManager():
        return get_ro_server()


class RunRevisionMailJobs(LaunchpadCronScript):
    """Run pending branch mail jobs."""

    def main(self):
        globalErrorUtility.configure('sendbranchmail')
        runner = JobRunner.runFromSource(
            BranchMailJobSource, 'send-branch-mail', logging.getLogger())
        self.logger.info(
            'Ran %d RevisionMailJobs.' % len(runner.completed_jobs))


if __name__ == '__main__':
    script = RunRevisionMailJobs(
        'sendbranchmail', config.sendbranchmail.dbuser)
    script.lock_and_run()

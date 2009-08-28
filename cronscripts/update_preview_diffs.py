#!/usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Update or create previews diffs for branch merge proposals."""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from lp.codehosting.vfs import get_scanner_server
from lp.services.job.runner import JobRunner
from lp.code.interfaces.branchmergeproposal import (
    IUpdatePreviewDiffJobSource,)
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class JobCronScript(LaunchpadCronScript):
    """Base class for scripts that run jobs."""

    def __init__(self):
        dbuser = getattr(config, self.config_name).dbuser
        super(JobCronScript, self).__init__(self.config_name, dbuser)

    def main(self):
        globalErrorUtility.configure(self.config_name)
        runner = JobRunner.fromReady(getUtility(self.source_interface))
        cleanups = self.setUp()
        try:
            runner.runAll()
        finally:
            for cleanup in reversed(cleanups):
                cleanup()
        self.logger.info(
            'Ran %d %s jobs.',
            len(runner.completed_jobs), self.source_interface.__name__)


class RunUpdatePreviewDiffJobs(JobCronScript):
    """Run UpdatePreviewDiff jobs."""

    config_name = 'update_preview_diffs'
    source_interface = IUpdatePreviewDiffJobSource

    def setUp(self):
        server = get_scanner_server()
        server.setUp()
        return [server.tearDown]


if __name__ == '__main__':
    script = RunUpdatePreviewDiffJobs()
    script.lock_and_run()

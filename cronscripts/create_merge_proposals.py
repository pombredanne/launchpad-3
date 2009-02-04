#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Create BranchMergeProposals from email."""

__metaclass__ = type

import _pythonpath
from zope.component import getUtility

from canonical.config import config
from canonical.codehosting.branchfs import get_scanner_server
from canonical.codehosting.jobs import JobRunner
from canonical.launchpad.interfaces.branchmergeproposal import (
    ICreateMergeProposalJobSource,)
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class RunCreateMergeProposalJobs(LaunchpadCronScript):
    """Run create merge proposal jobs."""

    def main(self):
        globalErrorUtility.configure('mpcreationjobs')
        job_source = getUtility(ICreateMergeProposalJobSource)
        runner = JobRunner.fromReady(job_source)
        server = get_scanner_server()
        server.setUp()
        try:
            runner.runAll()
        finally:
            server.tearDown()
        print 'Ran %d CreateMergeProposalJobs.' % len(runner.completed_jobs)


if __name__ == '__main__':
    script = RunCreateMergeProposalJobs(
        'sendcodemail', config.mpcreationjobs.dbuser)
    script.lock_and_run()

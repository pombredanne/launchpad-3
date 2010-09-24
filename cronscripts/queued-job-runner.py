#!/usr/bin/python -S
#
# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Handle any jobs that have a configured job category and db id."""

__metaclass__ = type

import _pythonpath


# The following line is a horrible hack, but unfortunately necessary right now
# to stop import errors from circular imports.
import canonical.launchpad.interfaces
from lp.registry.interfaces.persontransferjob import (
    IMembershipNotificationJobSource,
    )
from lp.services.job.runner import JobCronScript, TwistedJobRunner


class RunJobs(JobCronScript):
    """Run jobs."""

    config_name = 'queued-job-runner'
    source_interface = IMembershipNotificationJobSource

    def __init__(self):
        super(RunJobs, self).__init__(
            runner_class=TwistedJobRunner,
            script_name='queued-job-runner')


if __name__ == '__main__':
    from twisted.python import log
    import sys
    log.startLogging(sys.stdout)

    script = RunJobs()
    script.lock_and_run()

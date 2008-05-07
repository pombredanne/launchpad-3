# Copyright 2008 Canonical Ltd.  All rights reserved.

"""The code import dispatcher.

The code import dispatcher is responsible for checking if any code
imports need to be processed and launching child processes to handle
them.
"""

__metaclass__ = type
__all__ = [
    'CodeImportDispatcher',
    ]

import os
import socket
import subprocess

from canonical.codehosting import get_rocketfuel_root
from canonical.config import config


class CodeImportDispatcher:
    """A CodeImportDispatcher kicks off the processing of a job if needed.

    The entry point is `findAndDispatchJob`.

    :ivar txn: A transaction manager.
    :ivar logger: A `Logger` object.
    """

    worker_script = os.path.join(
        get_rocketfuel_root(), 'scripts', 'code-import-worker-db.py')

    def __init__(self, logger):
        """Initialize an instance.

        :param logger: A `Logger` object.
        """
        self.logger = logger

    def getHostname(self):
        """Return the hostname of this machine.

        This usually calls `socket.gethostname` but it can be
        overridden by the config for tests and developer machines.
        """
        if config.codeimportdispatcher.forced_hostname:
            return config.codeimportdispatcher.forced_hostname
        else:
            return socket.gethostname()

    def dispatchJob(self, job_id):
        """Start the processing of job `job_id`."""
        # Just launch the process and forget about it.
        log_file = os.path.join(
            config.codeimportdispatcher.worker_log_dir,
            'code-import-worker-%d.log' % (job_id,))
        # Return the Popen object to make testing easier.
        return subprocess.Popen(
            [self.worker_script, str(job_id), '-vv', '--log-file', log_file])


    def findAndDispatchJob(self, scheduler_client):
        """Check for and dispatch a job if necessary."""

        job_id = scheduler_client.getJobForMachine(self.getHostname())

        if job_id == 0:
            self.logger.info("No jobs pending.")
            return

        self.logger.info("Dispatching job %d." % job_id)

        self.dispatchJob(job_id)

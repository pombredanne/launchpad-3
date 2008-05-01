# Copyright 2008 Canonical Ltd.  All rights reserved.

"""The code import dispatcher.

The code import dispatcher is repsonsible for checking if any code
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

from zope.component import getUtility

from canonical.codehosting import get_rocketfuel_root
from canonical.config import config
from canonical.launchpad.interfaces import (
    CodeImportMachineOfflineReason, CodeImportMachineState,
    ICodeImportMachineSet)


class CodeImportDispatcher:
    """A CodeImportDispatcher kicks off the processing of a job if needed.

    The entry point is `dispatchJobs`.

    :ivar txn: A transaction manager.
    :ivar logger: A `Logger` object.
    """

    worker_script = os.path.join(
        get_rocketfuel_root(), 'scripts', 'code-import-worker-db.py')

    def __init__(self, txn, logger):
        """Initialize an instance.

        :param txn: A transaction manager.
        :param logger: A `Logger` object.
        """
        self.txn = txn
        self.logger = logger

    def getHostname(self):
        """Return the hostname of this machine.

        This usually calls `socket.gethostname` but it can be
        overriden by the config for tests and developer machines.
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

    def shouldLookForJob(self, machine):
        """Should we look for a job to run on this machine?

        There are three reasons we might not look for a job:

        a) The machine is OFFLINE
        b) The machine is QUIESCING (in which case we might go OFFLINE)
        c) There are already enough jobs running on this machine.
        """
        # XXX 2008-05-01 MichaelHudson: if this code was part of the
        # getJobForMachine call, this script wouldn't have to talk to the
        # database or even call execute_zcml_for_scripts().
        job_count = machine.current_jobs.count()

        if machine.state == CodeImportMachineState.OFFLINE:
            self.logger.info(
                "Machine is in OFFLINE state, not looking for jobs.")
            return False
        elif machine.state == CodeImportMachineState.QUIESCING:
            if job_count == 0:
                self.logger.info(
                    "Machine is in QUIESCING state and no jobs running, "
                    "going OFFLINE.")
                machine.setOffline(
                    CodeImportMachineOfflineReason.QUIESCED)
                # This is the only case where we modify the database.
                self.txn.commit()
                return False
            self.logger.info(
                "Machine is in QUIESCING state, not looking for jobs.")
            return False
        elif machine.state == CodeImportMachineState.ONLINE:
            max_jobs = config.codeimportdispatcher.max_jobs_per_machine
            return job_count < max_jobs
        else:
            raise AssertionError(
                "Unknown machine state %r??" % machine.state)

    def findAndDispatchJob(self, scheduler_client):
        """Check for and dispatch a job if necessary."""

        machine = getUtility(ICodeImportMachineSet).getByHostname(
            self.getHostname())

        if not self.shouldLookForJob(machine):
            return

        job_id = scheduler_client.getJobForMachine(machine.hostname)

        if job_id == 0:
            # There are no jobs that need to be run.
            self.logger.info(
                "No jobs pending.")
            return

        self.logger.info("Dispatching job %d." % job_id)

        self.dispatchJob(job_id)


# Copyright 2008 Canonical Ltd.  All rights reserved.

"""XXX."""

__metaclass__ = type
__all__ = [
    'CodeImportController',
    ]

import os
import socket
import subprocess
import xmlrpclib

from zope.component import getUtility

import canonical
from canonical.config import config
from canonical.launchpad.interfaces import (
    CodeImportMachineState, ICodeImportJobSet, ICodeImportMachineSet)


class CodeImportController:
    """XXX."""

    # XXX Note that this script does not exist yet :-)
    path_to_script = os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(canonical.__file__))),
        'scripts/code-import-worker.py')

    def __init__(self, logger):
        """XXX."""
        self.logger = logger
        self.machine = getUtility(ICodeImportMachineSet).getByHostname(
            self.getHostname())

    def getHostname(self):
        """XXX."""
        return socket.gethostname()

    def dispatchJob(self, job_id):
        """XXX."""
        # Just launch the process and forget about it.
        subprocess.Popen([self.worker_script, str(job_id)])

    def getJobId(self):
        """XXX."""
        server_proxy = xmlrpclib.ServerProxy(
            config.codeimport.codeimportscheduler_url)
        return server_proxy.getJobForMachine(self.machine.hostname)

    def dispatchJobs(self):
        """XXX."""

        if self.machine.state == CodeImportMachineState.OFFLINE:
            self.logger.info(
                "Machine is in OFFLINE state, not looking for jobs.")
            return

        job_set = getUtility(ICodeImportJobSet).getUtility()
        job_count = job_set.getJobsRunningOnMachine().count()

        if self.machine.state == CodeImportMachineState.QUIESCING:
            if job_count == 0:
                self.logger.info(
                    "Machine is in QUIESCING state and no jobs running, "
                    "going OFFLINE.")
                self.machine.goOffline()
                # This is the only case where we modify the database.
                self.txn.commit()
                return
            self.logger.info(
                "Machine is in QUIESCING state, not looking for jobs.")
            return

        if job_count > 9: # Magic number!
            # There are enough jobs running on this machine already.
            return

        job_id = self.getJobId()

        if job_id == 0:
            # There are no jobs that need to be run.
            self.logger.info(
                "No jobs pending.")
            return

        self.logger.info("Dispatching job %d." % job_id)

        self.dispatchJob(job_id)


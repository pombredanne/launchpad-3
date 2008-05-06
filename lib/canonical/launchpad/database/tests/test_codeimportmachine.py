# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of CodeImportMachine.

Other tests are in codeimport-machine.txt."""

import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import (
    CodeImportMachineOfflineReason, CodeImportMachineState,
    ICodeImportJobWorkflow)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import LaunchpadFunctionalLayer

class TestCodeImportMachineShouldLookForJob(unittest.TestCase):
    """Tests for  `CodeImportMachine.shouldLookForJob`."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        self.factory = LaunchpadObjectFactory()
        self.machine = self.factory.makeCodeImportMachine(set_online=True)

    def createJobRunningOnMachine(self, machine):
        """Create a job in the database and mark it as running on `machine`.
        """
        job = self.factory.makeCodeImportJob()
        getUtility(ICodeImportJobWorkflow).startJob(job, machine)
        flush_database_updates()

    def test_machineIsOffline(self):
        # When the machine is offline, we shouldn't look for any jobs.
        self.machine.setOffline(CodeImportMachineOfflineReason.STOPPED)
        self.assertFalse(self.machine.shouldLookForJob())

    def test_machineIsQuiescingNoJobsRunning(self):
        # When the machine is quiescing and no jobs are running on this
        # machine, we should set the machine to OFFLINE and not look for jobs.
        self.machine.setQuiescing(self.factory.makePerson(), "reason")
        self.assertFalse(self.machine.shouldLookForJob())
        self.assertEqual(self.machine.state, CodeImportMachineState.OFFLINE)

    def test_machineIsQuiescingWithJobsRunning(self):
        # When the machine is quiescing and there are jobs running on this
        # machine, we shouldn't look for any more jobs.
        self.createJobRunningOnMachine(self.machine)
        self.machine.setQuiescing(self.factory.makePerson(), "reason")
        self.assertFalse(self.machine.shouldLookForJob())
        self.assertEqual(self.machine.state, CodeImportMachineState.QUIESCING)

    def test_enoughJobsRunningOnMachine(self):
        # When there are already enough jobs running on this machine, we
        # shouldn't look for any more jobs.
        for i in range(config.codeimportdispatcher.max_jobs_per_machine):
            self.createJobRunningOnMachine(self.machine)
        self.assertFalse(self.machine.shouldLookForJob())

    def test_shouldLook(self):
        # If the machine is online and there are not already
        # max_jobs_per_machine jobs running, then we should look for a job.
        self.assertTrue(self.machine.shouldLookForJob())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

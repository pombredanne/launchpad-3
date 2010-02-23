# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type

import unittest
import xmlrpclib

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.xmlrpc.faults import NoSuchCodeImportJob
from canonical.launchpad.testing.codeimporthelpers import make_running_import
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.code.model.codeimportjob import CodeImportJob
from lp.code.xmlrpc.codeimportscheduler import CodeImportSchedulerAPI
from lp.codehosting.codeimport.worker import CodeImportSourceDetails
from lp.testing import run_with_login, TestCaseWithFactory


class TestCodeImportSchedulerAPI(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.api = CodeImportSchedulerAPI(None, None)
        self.machine = self.factory.makeCodeImportMachine(set_online=True)
        for job in CodeImportJob.select():
            job.destroySelf()

    def makeCodeImportJob(self, running):
        person = getUtility(ILaunchpadCelebrities).vcs_imports.teamowner
        if running:
            return removeSecurityProxy(run_with_login(person, make_running_import)).import_job
        else:
            return run_with_login(person, self.factory.makeCodeImportJob)

    def test_getJobForMachine_no_job_waiting(self):
        # If no job is waiting getJobForMachine returns 0.
        job_id = self.api.getJobForMachine(self.machine.hostname, 10)
        self.assertEqual(0, job_id)

    def test_getJobForMachine_job_waiting(self):
        # If a job is waiting getJobForMachine returns its id.
        code_import_job = self.makeCodeImportJob(running=False)
        job_id = self.api.getJobForMachine(self.machine.hostname, 10)
        self.assertEqual(code_import_job.id, job_id)

    def test_getImportDataForJobID(self):
        # getImportDataForJobID
        code_import_job = self.makeCodeImportJob(running=True)
        code_import = removeSecurityProxy(code_import_job).code_import
        code_import_arguments, branch_url, log_file_name = \
            self.api.getImportDataForJobID(code_import_job.id)
        import_as_arguments = CodeImportSourceDetails.fromCodeImport(
            code_import).asArguments()
        expected_log_file_name = '%s.log' % (
            code_import.branch.unique_name[1:].replace('/', '-'))
        self.assertEqual(
            (import_as_arguments, canonical_url(code_import.branch),
             expected_log_file_name),
            (code_import_arguments, branch_url, log_file_name))

    def test_getImportDataForJobID_not_found(self):
        # getImportDataForJobID returns a NoSuchCodeImportJob fault when there
        # is no code import job with the given ID.
        fault = self.api.getImportDataForJobID(-1)
        self.assertTrue(
            isinstance(fault, xmlrpclib.Fault),
            "getImportDataForJobID(-1) returned %r, not a Fault."
            % (fault,))
        self.assertEqual(NoSuchCodeImportJob, fault.__class__)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


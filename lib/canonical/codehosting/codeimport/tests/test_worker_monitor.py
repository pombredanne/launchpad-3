# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type


from twisted.trial.unittest import TestCase

from zope.component import getUtility

from canonical.database.
from canonical.launchpad.interfaces import ICodeImportJobSet


class TestWorkerMonitorIntegration(TestCase):

    def setUp(self):
        self.nukeCodeImportSampleData()
        self.subversion_server = SubversionServer()
        self.subversion_server.setUp()
        self.addCleanup(self.subversion_server.tearDown)
        self.repo_path = tempfile.mkdtmp()
        self.addCleanup(lambda : shutil.rmtree(self.repo_path))
        self.subversion_server.makeRepository(self.repo_path, 'stuff')
        self.machine = self.factory.makeCodeImportMachine(online=True)

    def getStartedJob(self):
        code_import = self.createApprovedCodeImport(
            svn_branch_url=self.repo_path)
        job = getUtility(ICodeImportJobSet).getJobForMachine(self.machine)
        assert code_import == job
        return job

    def test_import(self):
        job = self.getDueJob()
        code_import_id = job.code_import.id
        job_id = job.id
        commit()
        result = CodeImportWorkerMonitor(job_id).run()
        def check_result(ignored):
            self.checkCodeImportResultCreated()
            self.checkBranchImportedOKForCodeImport(code_import_id)
            return ignored
        return result.addCallback(check_result)

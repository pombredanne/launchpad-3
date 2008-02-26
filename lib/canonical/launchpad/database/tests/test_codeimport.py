# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of CodeImport and CodeImportSet."""
import unittest

from canonical.launchpad.database import (
    CodeImportJobSet,
    CodeImportSet,
    )
from canonical.launchpad.ftests import syncUpdate
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import LaunchpadZopelessLayer

class TestCodeImportDeletion(unittest.TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.factory = LaunchpadObjectFactory()

    def test_delete(self):
        code_import = self.factory.makeCodeImport()
        CodeImportSet().delete(code_import)

    def test_deleteIncludesJob(self):
        code_import = self.factory.makeCodeImport()
        code_import_job = self.factory.makeCodeImportJob(code_import)
        job_id = code_import_job.id
        CodeImportJobSet().getById(job_id)
        job = CodeImportJobSet().getById(job_id)
        assert job is not None
        CodeImportSet().delete(code_import)
        job = CodeImportJobSet().getById(job_id)
        assert job is None


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

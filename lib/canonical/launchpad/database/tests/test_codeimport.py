# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of CodeImport and CodeImportSet."""
import unittest

from sqlobject import SQLObjectNotFound

from canonical.launchpad.database import (
    CodeImportEvent,
    CodeImportJobSet,
    CodeImportSet,
    CodeImportResult,
    )
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

    def test_deleteIncludesEvent(self):
        code_import_event = self.factory.makeCodeImportEvent()
        code_import_event_id = code_import_event.id
        CodeImportEvent.get(code_import_event_id)
        CodeImportSet().delete(code_import_event.code_import)
        self.assertRaises(
            SQLObjectNotFound, CodeImportEvent.get, code_import_event_id)

    def test_deleteIncludesResult(self):
        code_import_result = self.factory.makeCodeImportResult()
        code_import_result_id = code_import_result.id
        CodeImportResult.get(code_import_result_id)
        CodeImportSet().delete(code_import_result.code_import)
        self.assertRaises(
            SQLObjectNotFound, CodeImportResult.get, code_import_result_id)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Testing rosetta-branches cronscript.

This would normally be done in a doctest but TestCaseWithFactory has all the
provisions to handle Bazaar branches.
"""

__metaclass__ = type

from unittest import TestLoader

from bzrlib.revision import NULL_REVISION
from canonical.testing import ZopelessAppServerLayer
import transaction
from zope.component import getUtility

from canonical.launchpad.database.branchjob import RosettaUploadJob
from canonical.launchpad.interfaces.translations import (
    TranslationsBranchImportMode)
from canonical.launchpad.interfaces.translationimportqueue import (
    ITranslationImportQueue, RosettaImportStatus)
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.testing import TestCaseWithFactory

class TestRosettaBranchesScript(TestCaseWithFactory):
    """Testing the rosetta-bazaar cronscript."""

    layer = ZopelessAppServerLayer

    def _clear_import_queue(self):
        # The testdata has entries in the queue.
        queue = getUtility(ITranslationImportQueue)
        entries = list(queue)
        for entry in entries:
            queue.remove(entry)

    def test_rosetta_branches_script(self):
        # If a job exists it will be executed and the template file will
        # be put into the import queue with status "Approved".
        self._clear_import_queue()
        self.useTempBzrHome()
        pot_path = self.factory.getUniqueString() + ".pot"
        pot_content = self.factory.getUniqueString()
        branch, tree = self.createMirroredBranchAndTree()
        tree.bzrdir.root_transport.put_bytes(pot_path, pot_content)
        tree.add(pot_path)
        revision_id = tree.commit("first commit")
        branch.last_scanned_id = revision_id
        branch.last_mirrored_id = revision_id
        series = self.factory.makeProductSeries()
        series.branch = branch
        series.translations_autoimport_mode = (
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        job = RosettaUploadJob.create(branch, NULL_REVISION)
        transaction.commit()

        return_code, stdout, stderr = run_script(
            'cronscripts/rosetta-branches.py', [])
        self.assertEqual(0, return_code)
        self.assertEqual("", stdout)
        self.assertInString("Ran 1 RosettaBranchJobs", stderr)

        queue = getUtility(ITranslationImportQueue)
        self.assertEqual(1, queue.entryCount())
        entry = list(queue)[0]
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)
        self.assertEqual(pot_path, entry.path)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
from unittest import TestLoader

from lp.testing import TestCase

from canonical.buildd.generate_translation_templates import (
    GenerateTranslationTemplates)

from canonical.launchpad.ftests.script import run_script
from canonical.testing.layers import ZopelessDatabaseLayer


class MockGenerateTranslationTemplates(GenerateTranslationTemplates):
    """A GenerateTranslationTemplates with mocked _checkout."""
    # Records, for testing purposes, whether this object checked out a
    # branch.
    checked_out_branch = False

    def _checkout(self, branch_url):
        assert not self.checked_out_branch, "Checking out branch again!"
        self.checked_out_branch = True


class TestGenerateTranslationTemplates(TestCase):
    """Test slave-side generate-translation-templates script."""
    def test_getBranch_url(self):
        # If passed a branch URL, the template generation script will
        # check out that branch into a directory called "source-tree."
        branch_url = 'lp://~my/translation/branch'

        generator = MockGenerateTranslationTemplates(branch_url)
        generator._getBranch()

        self.assertTrue(generator.checked_out_branch)
        self.assertTrue(generator.branch_dir.endswith('source-tree'))

    def test_getBranch_dir(self):
        # If passed a branch directory, the template generation script
        # works directly in that directory.
        branch_dir = '/home/me/branch'

        generator = MockGenerateTranslationTemplates(branch_dir)
        generator._getBranch()

        self.assertFalse(generator.checked_out_branch)
        self.assertEqual(branch_dir, generator.branch_dir)

    def test_script(self):
        tempdir = self.makeTemporaryDirectory()
        (retval, out, err) = run_script(
            'lib/canonical/buildd/generate_translation_templates.py',
            args=[tempdir])
        self.assertEqual(0, retval)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from unittest import TestLoader

from lp.testing import TestCaseWithFactory

from canonical.buildd.generate_translation_templates import (
    GenerateTranslationTemplates)

from canonical.launchpad.ftests.script import run_script
from canonical.testing.layers import ZopelessDatabaseLayer


class TestGenerateTranslationTemplates(TestCaseWithFactory):
    """Test slave-side generate-translation-templates script."""
    layer = ZopelessDatabaseLayer

    def test_checkout(self):
# XXX: Test branch checkout.
        #branch_url = 'a branch URL'
        #generator = GenerateTranslationTemplates(branch_url)
        pass

    def test_script(self):
        tempdir = self.makeTemporaryDirectory()
        (retval, out, err) = run_script(
            'lib/canonical/buildd/generate_translation_templates.py',
            args=[tempdir])
        self.assertEqual(0, retval)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

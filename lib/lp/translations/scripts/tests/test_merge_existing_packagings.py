# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the merge_translations script."""


from textwrap import dedent

import transaction

from canonical.launchpad.scripts.tests import run_script
from canonical.testing.layers import ZopelessAppServerLayer
from lp.translations.translationmerger import TranslationMerger
from lp.testing import TestCaseWithFactory


class TestMergeExistingPackagings(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_merge_translations(self):
        from lp.translations.tests.test_translationmergejob import (
            TestTranslationMergeJob,
            )
        # Import here to avoid autodetection by test runner.
        for packaging in set(TranslationMerger.findMergeablePackagings()):
            packaging.destroySelf()
        job = TestTranslationMergeJob.makeTranslationMergeJob(self.factory)
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'scripts/rosetta/merge-existing-packagings.py', [],
            expect_returncode=0)
        self.assertEqual('', stderr)
        self.assertEqual('', stdout)
        self.assertEqual(1, TestTranslationMergeJob.countTranslations(job))

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the merge_translations script."""


from textwrap import dedent

import transaction

from canonical.launchpad.scripts.tests import run_script
from canonical.testing.layers import ZopelessAppServerLayer
from lp.testing import TestCaseWithFactory
from lp.translations.tests.test_translationpackagingjob import (
    count_translations,
    make_translation_merge_job,
    )


class TestMergeTranslations(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_merge_translations(self):
        job = make_translation_merge_job(self.factory)
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/run_jobs.py', ['merge_translations'],
            expect_returncode=0)
        self.assertEqual(dedent("""\
            INFO    Creating lockfile: /var/lock/launchpad-jobcronscript.lock
            INFO    Running synchronously.
            INFO    Deleted POTMsgSets: 1.  TranslationMessages: 1.
            INFO    Ran 1 TranslationMergeJob jobs.
            """), stderr)
        self.assertEqual('', stdout)
        self.assertEqual(1, count_translations(job))

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for our Sphinx documentation."""

__metaclass__ = type

import os
from StringIO import StringIO

from fixtures import MonkeyPatch
import sphinx

from canonical.config import config
from lp.testing import TestCase


class TestSphinxDocumentation(TestCase):
    """Is our Sphinx documentation building correctly?"""

    def test_docs_build_without_error(self):
        # The Sphinx documentation must build without errors or warnings.
        stdout = StringIO()
        stderr = StringIO()
        self.useFixture(MonkeyPatch('sys.stdout', stdout))
        self.useFixture(MonkeyPatch('sys.stderr', stderr))
        output_dir = self.makeTemporaryDirectory()
        doc_dir = os.path.join(config.root, 'doc')
        returncode = sphinx.main(
            ['sphinx-build', '-d', '%s/doctrees' % output_dir,
             '-aNq', doc_dir, '%s/html' % output_dir])
        self.assertEqual(0, returncode)
        self.assertEqual('Making output directory...\n', stderr.getvalue())
        self.assertEqual('', stdout.getvalue())

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for our Sphinx documentation."""

__metaclass__ = type

import os

import sphinx

from canonical.config import config
from lp.services.utils import run_capturing_output
from lp.testing import TestCase


class TestSphinxDocumentation(TestCase):
    """Is our Sphinx documentation building correctly?"""

    def test_docs_build_without_error(self):
        # The Sphinx documentation must build without errors or warnings.
        output_dir = self.makeTemporaryDirectory()
        doc_dir = os.path.join(config.root, 'doc')
        returncode, stdout, stderr = run_capturing_output(
            sphinx.main,
            ['sphinx-build', '-d', '%s/doctrees' % output_dir,
             '-aNq', doc_dir, '%s/html' % output_dir])
        self.assertEqual(0, returncode)
        self.assertEqual('Making output directory...\n', stderr)
        self.assertEqual('', stdout)

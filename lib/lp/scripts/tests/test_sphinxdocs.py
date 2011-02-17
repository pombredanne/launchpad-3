# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for our Sphinx documentation."""

__metaclass__ = type

import os
import subprocess

from canonical.config import config
from lp.testing import TestCase


class TestSphinxDocumentation(TestCase):
    """Is our Sphinx documentation building correctly?"""

    def runProcess(self, args):
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr

    def test_docs_build_without_error(self):
        # The Sphinx documentation must build without errors or warnings.
        output_dir = self.makeTemporaryDirectory()
        doc_dir = os.path.join(config.root, 'doc')
        returncode, stdout, stderr = self.runProcess(
            ['sphinx-build', '-d', '%s/doctrees' % output_dir,
             '-aNq', doc_dir, '%s/html' % output_dir])
        self.assertEqual(0, returncode)
        self.assertEqual('Making output directory...\n', stderr)
        self.assertEqual('', stdout)

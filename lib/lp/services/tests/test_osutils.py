# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.services.osutils."""

__metaclass__ = type

import os
import tempfile
import unittest

from lp.services.osutils import remove_tree
from lp.testing import TestCase


class TestRemoveTree(TestCase):
    """Tests for remove_tree."""

    def test_removes_directory(self):
        # remove_tree deletes the directory.
        directory = tempfile.mkdtemp()
        remove_tree(directory)
        self.assertFalse(os.path.isdir(directory))
        self.assertFalse(os.path.exists(directory))

    def test_on_nonexistent_path_passes_silently(self):
        # remove_tree simply does nothing when called on a non-existent path.
        directory = tempfile.mkdtemp()
        nonexistent_tree = os.path.join(directory, 'foo')
        remove_tree(nonexistent_tree)
        self.assertFalse(os.path.isdir(nonexistent_tree))
        self.assertFalse(os.path.exists(nonexistent_tree))

    def test_raises_on_file(self):
        # If remove_tree is pased a file, it raises an OSError.
        directory = tempfile.mkdtemp()
        filename = os.path.join(directory, 'foo')
        fd = open(filename, 'w')
        fd.write('data')
        fd.close()
        self.assertRaises(OSError, remove_tree, filename)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

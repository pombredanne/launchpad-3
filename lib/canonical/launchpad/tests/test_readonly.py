# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os

from lp.testing import TestCase

from canonical.launchpad.readonly import is_read_only


class TestReadOnlyMode(TestCase):

    def test_is_read_only(self):
        # By default we run in read-write mode.
        self.assertFalse(is_read_only())

        # When a file named 'read-only.txt' exists under the root of the tree,
        # we run in read-only mode.
        root = os.path.join(
            os.path.dirname(__file__), os.pardir, os.pardir, os.pardir,
            os.pardir)
        file_path = os.path.join(root, 'read-only.txt')
        f = open(file_path, 'w')
        f.close()
        self.assertTrue(is_read_only())
        os.remove(file_path)

        # Once the file is removed, we're back into read-write mode.
        self.assertFalse(is_read_only())

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.testing import TestCase

from canonical.launchpad.readonly import (
    is_read_only, remove_read_only_file, touch_read_only_file)


class TestReadOnlyMode(TestCase):

    def test_is_read_only(self):
        # By default we run in read-write mode.
        self.assertFalse(is_read_only())

        # When a file named 'read-only.txt' exists under the root of the tree,
        # we run in read-only mode.
        touch_read_only_file()
        self.assertTrue(is_read_only())
        remove_read_only_file()

        # Once the file is removed, we're back into read-write mode.
        self.assertFalse(is_read_only())

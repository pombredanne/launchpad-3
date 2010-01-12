# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility

from lazr.restful.utils import get_current_browser_request

from lp.testing import TestCase

from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.readonly import (
    IIsReadOnly, read_only_file_exists, _remove_read_only_file,
    _touch_read_only_file, READ_ONLY_MODE_ANNOTATIONS_KEY)
from canonical.testing.layers import FunctionalLayer


class TestReadOnlyModeDetection(TestCase):

    def test_read_only_file_exists(self):
        # By default we run in read-write mode.
        self.assertFalse(read_only_file_exists())

        # When a file named 'read-only.txt' exists under the root of the tree,
        # we run in read-only mode.
        _touch_read_only_file()
        try:
            self.assertTrue(read_only_file_exists())
        finally:
            _remove_read_only_file()

        # Once the file is removed, we're back into read-write mode.
        self.assertFalse(read_only_file_exists())


class TestIsReadOnlyUtility(TestCase):
    layer = FunctionalLayer

    def tearDown(self):
        # Safety net just in case a test leaves the read-only.txt file behind.
        if read_only_file_exists():
            _remove_read_only_file()

    def test_isReadOnly(self):
        # By default we run in read-write mode.
        logout()
        utility = getUtility(IIsReadOnly)
        self.assertFalse(utility.isReadOnly())

        # When a file named 'read-only.txt' exists under the root of the tree,
        # we run in read-only mode.
        _touch_read_only_file()
        try:
            self.assertTrue(utility.isReadOnly())
        finally:
            _remove_read_only_file()

    def test_caching_in_request(self):
        # When called as part of a request processing,
        # IIsReadOnly.isReadOnly() will stash the read-only flag in the
        # request's annotations.
        login(ANONYMOUS)
        request = get_current_browser_request()
        self.assertIs(
            None,
            request.annotations.get(READ_ONLY_MODE_ANNOTATIONS_KEY))
        self.assertFalse(getUtility(IIsReadOnly).isReadOnly())
        self.assertFalse(
            request.annotations.get(READ_ONLY_MODE_ANNOTATIONS_KEY))

    def test_cached_value_takes_precedence(self): 
        # Once the request has the read-only flag, we don't check for the
        # presence of the read-only.txt file anymore, so it could be removed
        # and the request would still be in read-only mode.
        login(ANONYMOUS)
        request = get_current_browser_request()
        request.annotations[READ_ONLY_MODE_ANNOTATIONS_KEY] = True
        self.assertTrue(getUtility(IIsReadOnly).isReadOnly())
        self.assertFalse(read_only_file_exists())

    def test_logging_mode_changes(self):
        # XXX: Fill me!
        pass

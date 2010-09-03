# Copyright 2010 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = []

from canonical.launchpad.browser.librarian import (
    StreamOrRedirectLibraryFileAliasView,
    )
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.librarian.interfaces import LibrarianServerError
from lp.testing import TestCase


class FakeRestrictedLibraryFileAlias:
    deleted = False
    restricted = True

    def open(self):
        raise LibrarianServerError('Librarian is down')


class TestStreamOrRedirectLibraryFileAliasView(TestCase):

    def test_restricted_file_when_librarian_is_down(self):
        view = StreamOrRedirectLibraryFileAliasView(
            FakeRestrictedLibraryFileAlias(), LaunchpadTestRequest())
        html = view()
        self.assertEqual(503, view.request.response.getStatus())
        self.assertIn(
            'There was a problem fetching the contents of this file', html)

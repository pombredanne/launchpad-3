# Copyright 2010 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = []

import re

from canonical.launchpad.browser.librarian import (
    ProxiedLibraryFileAlias,
    StreamOrRedirectLibraryFileAliasView,
    )
from canonical.launchpad.webapp.interaction import (
    get_current_principal,
    setupInteraction,
    )
from canonical.launchpad.webapp.servers import (
    LaunchpadTestRequest,
    WebServiceTestRequest,
    )
from canonical.librarian.interfaces import LibrarianServerError
from canonical.testing import LaunchpadFunctionalLayer
from lp.testing import (
    login_person,
    TestCase,
    TestCaseWithFactory,
    )


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


class TestProxiedLibraryFileAlias(TestCaseWithFactory):
    """Tests for ProxiedLibraryFileAlias."""

    layer = LaunchpadFunctionalLayer

    url_pattern = r'^(.*?)\d+(.*)\d+(.*)$'

    def setUp(self):
        super(TestProxiedLibraryFileAlias, self).setUp()
        user = self.factory.makePerson()
        login_person(user)
        bugattachment = self.factory.makeBugAttachment(filename='foo.txt')
        self.proxied_lfa = ProxiedLibraryFileAlias(
            bugattachment.libraryfile, bugattachment)

    def setUpWebInteraction(self):
        principal = get_current_principal()
        environment = {
            'SERVER_URL': 'http://bugs.launchpad.dev',
            }
        setupInteraction(
            principal=principal,
            participation=LaunchpadTestRequest(environ=environment))

    def setUpApiInteraction(self):
        principal = get_current_principal()
        setupInteraction(
            principal=principal,
            participation=WebServiceTestRequest(SCRIPT_NAME='api/devel'))

    def test_http_url(self):
        # ProxiedLibraryFileAlias.http_url returns a URL relative to
        # a parent object.
        self.setUpWebInteraction()
        mo = re.search(self.url_pattern, self.proxied_lfa.http_url)
        self.assertEqual(
            ('http://bugs.launchpad.dev/bugs/', '/+attachment/',
             '/+files/foo.txt'),
            mo.groups())

    def test_http_url_in_webservice_request(self):
        # ProxiedLibraryFileAlias.http_url returns the regular URL
        # even for webservice requests.
        self.setUpApiInteraction()
        mo = re.search(self.url_pattern, self.proxied_lfa.http_url)
        self.assertEqual(
            ('http://bugs.launchpad.dev/bugs/', '/+attachment/',
             '/+files/foo.txt'),
            mo.groups())

    def test_api_url(self):
        # ProxiedLibraryFileAlias.api_url returns a webservice URL relative
        # to a parent object.
        self.setUpApiInteraction()
        mo = re.search(self.url_pattern, self.proxied_lfa.api_url)
        self.assertEqual(
            ('http://api.launchpad.dev/api/devel/bugs/', '/+attachment/',
             '/+files/foo.txt'),
            mo.groups())

    def test_api_url_in_regular_request(self):
        # ProxiedLibraryFileAlias.api_url returns the webserice URL
        # even for regular HTTP requests.
        self.setUpWebInteraction()
        mo = re.search(self.url_pattern, self.proxied_lfa.api_url)
        self.assertEqual(
            ('http://bugs.launchpad.dev/api/devel/bugs/', '/+attachment/',
             '/+files/foo.txt'),
            mo.groups())

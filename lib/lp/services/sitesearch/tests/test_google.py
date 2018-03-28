# Copyright 2011-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the google search service."""

__metaclass__ = type


from fixtures import MockPatch
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    )

from lp.services.sitesearch import GoogleSearchService
from lp.services.sitesearch.interfaces import SiteSearchResponseError
from lp.services.timeout import TimeoutError
from lp.testing import TestCase
from lp.testing.layers import LaunchpadFunctionalLayer


class TestGoogleSearchService(TestCase):
    """Test GoogleSearchService."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestGoogleSearchService, self).setUp()
        self.search_service = GoogleSearchService()

    def test_search_converts_HTTPError(self):
        # The method converts HTTPError to SiteSearchResponseError.
        args = ('url', 500, 'oops', {}, None)
        self.useFixture(MockPatch(
            'lp.services.sitesearch.urlfetch', side_effect=HTTPError(*args)))
        self.assertRaises(
            SiteSearchResponseError, self.search_service.search, 'fnord')

    def test_search_converts_ConnectionError(self):
        # The method converts ConnectionError to SiteSearchResponseError.
        self.useFixture(MockPatch(
            'lp.services.sitesearch.urlfetch',
            side_effect=ConnectionError('oops')))
        self.assertRaises(
            SiteSearchResponseError, self.search_service.search, 'fnord')

    def test_search_converts_TimeoutError(self):
        # The method converts TimeoutError to SiteSearchResponseError.
        self.useFixture(MockPatch(
            'lp.services.sitesearch.urlfetch',
            side_effect=TimeoutError('oops')))
        self.assertRaises(
            SiteSearchResponseError, self.search_service.search, 'fnord')

    def test___parse_google_search_protocol_SyntaxError(self):
        # The method converts SyntaxError to SiteSearchResponseError.
        self.useFixture(MockPatch(
            'lp.services.timeout.urlfetch', side_effect=SyntaxError('oops')))
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service._parse_google_search_protocol, '')

    def test___parse_google_search_protocol_IndexError(self):
        # The method converts IndexError to SiteSearchResponseError.
        self.useFixture(MockPatch(
            'lp.services.timeout.urlfetch', side_effect=IndexError('oops')))
        data = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            '<GSP VER="3.2"></GSP>')
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service._parse_google_search_protocol, data)

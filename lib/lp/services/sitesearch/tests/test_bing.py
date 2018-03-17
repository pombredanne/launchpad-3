# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the bing search service."""

__metaclass__ = type

from contextlib import contextmanager

from requests.exceptions import (
    ConnectionError,
    HTTPError,
    )

from lp.services.sitesearch import BingSearchService
from lp.services.sitesearch.interfaces import BingResponseError
from lp.services.timeout import TimeoutError
from lp.testing import TestCase
from lp.testing.layers import (
    BingLaunchpadFunctionalLayer,
    LaunchpadFunctionalLayer,
    )


@contextmanager
def urlfetch_exception(test_error, *args):
    """Raise an error during the execution of urlfetch.

    This function replaces urlfetch() with a function that
    raises an error.
    """

    def raise_exception(url):
        raise test_error(*args)

    from lp.services import timeout
    original_urlfetch = timeout.urlfetch
    timeout.urlfetch = raise_exception
    try:
        yield
    finally:
        timeout.urlfetch = original_urlfetch


class TestBingSearchService(TestCase):
    """Test GoogleSearchService."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBingSearchService, self).setUp()
        self.search_service = BingSearchService()

    def test_search_converts_HTTPError(self):
        # The method converts HTTPError to BingResponseError.
        args = ('url', 500, 'oops', {}, None)
        with urlfetch_exception(HTTPError, *args):
            self.assertRaises(
                BingResponseError, self.search_service.search, 'fnord')

    def test_search_converts_ConnectionError(self):
        # The method converts ConnectionError to BingResponseError.
        with urlfetch_exception(ConnectionError, 'oops'):
            self.assertRaises(
                BingResponseError, self.search_service.search, 'fnord')

    def test_search_converts_TimeoutError(self):
        # The method converts TimeoutError to BingResponseError.
        with urlfetch_exception(TimeoutError, 'oops'):
            self.assertRaises(
                BingResponseError, self.search_service.search, 'fnord')

    def test_parse_bing_reponse_TypeError(self):
        # The method converts TypeError to BingResponseError.
        self.assertRaises(
            BingResponseError,
            self.search_service._parse_bing_response, None)

    def test_parse_bing_reponse_ValueError(self):
        # The method converts ValueError to BingResponseError.
        self.assertRaises(
            BingResponseError,
            self.search_service._parse_bing_response, '')

    def test_parse_bing_reponse_KeyError(self):
        # The method converts KeyError to BingResponseError.
        self.assertRaises(
            BingResponseError,
            self.search_service._parse_bing_response, '{}')


class FunctionalTestBingSearchService(TestCase):
    """Test GoogleSearchService."""

    layer = BingLaunchpadFunctionalLayer

    def setUp(self):
        super(FunctionalTestBingSearchService, self).setUp()
        self.search_service = BingSearchService()

    def test_search_with_results(self):
        matches = self.search_service.search('bug')
        self.assertEqual(0, matches.start)
        self.assertEqual(87000, matches.total)
        self.assertEqual(20, len(matches))

    def test_search_with_results_and_offset(self):
        matches = self.search_service.search('bug', start=20)
        self.assertEqual(20, matches.start)
        self.assertEqual(87000, matches.total)
        self.assertEqual(15, len(matches))

    def test_search_no_results(self):
        matches = self.search_service.search('fnord')
        self.assertEqual(0, matches.start)
        self.assertEqual(0, matches.total)
        self.assertEqual(0, len(matches))

    def test_search_no_meaningful_results(self):
        matches = self.search_service.search('no-meaningful')
        self.assertEqual(0, matches.start)
        self.assertEqual(0, matches.total)
        self.assertEqual(0, len(matches))

    def test_search_incomplete_response(self):
        self.assertRaises(
            BingResponseError,
            self.search_service.search, 'gnomebaker')

    def test_search_error_response(self):
        self.assertRaises(
            BingResponseError,
            self.search_service.search, 'errors-please')

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the google search service."""

__metaclass__ = type

from contextlib import contextmanager
from urllib2 import (
    HTTPError,
    URLError,
    )

from canonical.lazr.timeout import TimeoutError
from canonical.testing.layers import FunctionalLayer
from lp.services.search.google import GoogleSearchService
from lp.services.search.interfaces import GoogleResponseError
from lp.testing import TestCase


@contextmanager
def urlfetch_exception(test_error, *args):
    """Raise an error during the execution of urlfetch.

    This function replaces urlfetch() with a function that
    raises an error.
    """

    def raise_exception(url):
        raise test_error(*args)

    from canonical.lazr import timeout
    original_urlfetch = timeout.urlfetch
    timeout.urlfetch = raise_exception
    try:
        yield
    finally:
        timeout.urlfetch = original_urlfetch


class TestGoogleSearchService(TestCase):
    """Test GoogleSearchService."""

    layer = FunctionalLayer

    def test_search_converts_HTTPError(self):
        # The method converts HTTPError to GoogleResponseError.
        search_service = GoogleSearchService()
        args = ('url', 500, 'oops', {}, None)
        with urlfetch_exception(HTTPError, *args):
            self.assertRaises(
                GoogleResponseError, search_service.search, 'fnord')

    def test_search_converts_URLError(self):
        # The method converts URLError to GoogleResponseError.
        search_service = GoogleSearchService()
        with urlfetch_exception(URLError, 'oops'):
            self.assertRaises(
                GoogleResponseError, search_service.search, 'fnord')

    def test_search_converts_TimeoutError(self):
        # The method converts TimeoutError to GoogleResponseError.
        search_service = GoogleSearchService()
        with urlfetch_exception(TimeoutError, 'oops'):
            self.assertRaises(
                GoogleResponseError, search_service.search, 'fnord')

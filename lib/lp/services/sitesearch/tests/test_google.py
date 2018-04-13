# Copyright 2011-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the google search service."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from os import path

from fixtures import MockPatch
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    )
from testtools.matchers import HasLength

from lp.services.config import config
from lp.services.sitesearch import GoogleSearchService
from lp.services.sitesearch.interfaces import (
    GoogleWrongGSPVersion,
    SiteSearchResponseError,
    )
from lp.services.timeout import TimeoutError
from lp.testing import TestCase
from lp.testing.layers import GoogleLaunchpadFunctionalLayer


class TestGoogleSearchService(TestCase):
    """Test GoogleSearchService."""

    def setUp(self):
        super(TestGoogleSearchService, self).setUp()
        self.search_service = GoogleSearchService()
        self.base_path = path.normpath(
            path.join(path.dirname(__file__), 'data'))

    def test_configuration(self):
        self.assertEqual(config.google.site, self.search_service.site)
        self.assertEqual(
            config.google.client_id, self.search_service.client_id)

    def test_create_search_url(self):
        self.assertEndsWith(
            self.search_service.create_search_url(terms='svg +bugs'),
            '&q=svg+%2Bbugs&start=0')

    def test_create_search_url_escapes_unicode_chars(self):
        self.assertEndsWith(
            self.search_service.create_search_url('Carlo Perell\xf3 Mar\xedn'),
            '&q=Carlo+Perell%C3%B3+Mar%C3%ADn&start=0')

    def test_create_search_url_with_offset(self):
        self.assertEndsWith(
            self.search_service.create_search_url(terms='svg +bugs', start=20),
            '&q=svg+%2Bbugs&start=20')

    def test_create_search_url_empty_terms(self):
        e = self.assertRaises(
            ValueError, self.search_service.create_search_url, '')
        self.assertEqual("Missing value for parameter 'q'.", str(e))

    def test_create_search_url_null_terms(self):
        e = self.assertRaises(
            ValueError, self.search_service.create_search_url, None)
        self.assertEqual("Missing value for parameter 'q'.", str(e))

    def test_create_search_url_requires_start(self):
        e = self.assertRaises(
            ValueError, self.search_service.create_search_url, 'bugs', 'true')
        self.assertEqual("Value for parameter 'start' is not an int.", str(e))

    def test_parse_search_response_incompatible_param(self):
        """The PageMatches's start attribute comes from the GSP XML element
        '<PARAM name="start" value="0" original_value="0"/>'. When it cannot
        be found and the value cast to an int, an error is raised. There is
        nothing in the value attribute in the next test, so an error is raised.
        """
        file_name = path.join(
            self.base_path, 'googlesearchservice-incompatible-param.xml')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        assert '<M>' not in response

        e = self.assertRaises(
            GoogleWrongGSPVersion,
            self.search_service._parse_search_response, response)
        self.assertEqual(
            "Could not get the 'start' from the GSP XML response.", str(e))

    def test_parse_search_response_invalid_total(self):
        """The PageMatches's total attribute comes from the GSP XML element
        '<M>5</M>'. When it cannot be found and the value cast to an int,
        an error is raised. If Google were to redefine the meaning of the M
        element to use a '~' to indicate an approximate total, an error would
        be raised.
        """
        file_name = path.join(
            self.base_path, 'googlesearchservice-incompatible-matches.xml')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        assert '<M>~1</M>' in response

        e = self.assertRaises(
            GoogleWrongGSPVersion,
            self.search_service._parse_search_response, response)
        self.assertEqual(
            "Could not get the 'total' from the GSP XML response.", str(e))

    def test_parse_search_response_negative_total(self):
        """If the total is ever less than zero (see bug 683115),
        this is expected: we simply return a total of 0.
        """
        file_name = path.join(
            self.base_path, 'googlesearchservice-negative-total.xml')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        assert '<M>-1</M>' in response

        matches = self.search_service._parse_search_response(response)
        self.assertEqual(0, matches.total)

    def test_parse_search_response_missing_title(self):
        """A PageMatch requires a title, url, and a summary. If those elements
        ('<T>', '<U>', '<S>') cannot be found nested in an '<R>' a PageMatch
        cannot be made. A missing title (<T>) indicates a bad page on Launchpad
        so it is ignored. In this example, The first match is missing a title,
        so only the second page is present in the PageMatches.
        """
        file_name = path.join(
            self.base_path, 'googlesearchservice-missing-title.xml')
        with open(file_name, 'r') as response_file:
            response = response_file.read()

        matches = self.search_service._parse_search_response(response)
        self.assertThat(matches, HasLength(1))
        self.assertStartsWith(matches[0].title, 'Bug #205991 in Ubuntu:')
        self.assertEqual(
            'http://bugs.launchpad.dev/bugs/205991', matches[0].url)

    def test_parse_search_response_missing_summary(self):
        """When a match is missing a summary (<S>), it is skipped because
        there is no information about why it matched. This appears to relate to
        pages that are in the index, but should be removed. In this example
        taken from real data, the links are to the same page on different
        vhosts. The edge vhost has no summary, so it is skipped.
        """
        file_name = path.join(
            self.base_path, 'googlesearchservice-missing-summary.xml')
        with open(file_name, 'r') as response_file:
            response = response_file.read()

        matches = self.search_service._parse_search_response(response)
        self.assertThat(matches, HasLength(1))
        self.assertEqual('Blueprint: <b>Gobuntu</b> 8.04', matches[0].title)
        self.assertEqual(
            'http://blueprints.launchpad.dev/ubuntu/+spec/gobuntu-hardy',
            matches[0].url)

    def test_parse_search_response_missing_url(self):
        """When the URL (<U>) cannot be found the match is skipped. There are
        no examples of this. We do not want this hypothetical situation to give
        users a bad experience.
        """
        file_name = path.join(
            self.base_path, 'googlesearchservice-missing-url.xml')
        with open(file_name, 'r') as response_file:
            response = response_file.read()

        matches = self.search_service._parse_search_response(response)
        self.assertThat(matches, HasLength(1))
        self.assertEqual('Blueprint: <b>Gobuntu</b> 8.04', matches[0].title)
        self.assertEqual(
            'http://blueprints.launchpad.dev/ubuntu/+spec/gobuntu-hardy',
            matches[0].url)

    def test_parse_search_response_with_no_meaningful_results(self):
        """If no matches are found in the response, and there are 20 or fewer
        results, an Empty PageMatches is returned. This happens when the
        results are missing titles and summaries. This is not considered to be
        a problem because the small number implies that Google did a poor job
        of indexing pages or indexed the wrong Launchpad server. In this
        example, there is only one match, but the results is missing a title so
        there is not enough information to make a PageMatch.
        """
        file_name = path.join(
            self.base_path, 'googlesearchservice-no-meaningful-results.xml')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        assert '<M>1</M>' in response

        matches = self.search_service._parse_search_response(response)
        self.assertThat(matches, HasLength(0))

    def test_parse_search_response_with_incompatible_result(self):
        """If no matches are found in the response, and there are more than 20
        possible matches, an error is raised. Unlike the previous example there
        are lots of results; there is a possibility that the GSP version is
        incompatible. This example says it has 1000 matches, but none of the R
        tags can be parsed (because the markup was changed to use RESULT).
        """
        file_name = path.join(
            self.base_path, 'googlesearchservice-incompatible-result.xml')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        assert '<M>1000</M>' in response

        e = self.assertRaises(
            GoogleWrongGSPVersion,
            self.search_service._parse_search_response, response)
        self.assertEqual(
            "Could not get any PageMatches from the GSP XML response.", str(e))

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

    def test_parse_search_response_SyntaxError(self):
        # The method converts SyntaxError to SiteSearchResponseError.
        self.useFixture(MockPatch(
            'lp.services.sitesearch.urlfetch',
            side_effect=SyntaxError('oops')))
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service._parse_search_response, '')

    def test_parse_search_response_IndexError(self):
        # The method converts IndexError to SiteSearchResponseError.
        self.useFixture(MockPatch(
            'lp.services.sitesearch.urlfetch', side_effect=IndexError('oops')))
        data = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            '<GSP VER="3.2"></GSP>')
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service._parse_search_response, data)


class FunctionalGoogleSearchServiceTests(TestCase):
    """Test GoogleSearchService."""

    layer = GoogleLaunchpadFunctionalLayer

    def setUp(self):
        super(FunctionalGoogleSearchServiceTests, self).setUp()
        self.search_service = GoogleSearchService()

    def test_search_with_results(self):
        matches = self.search_service.search('bug')
        self.assertEqual(0, matches.start)
        self.assertEqual(25, matches.total)
        self.assertEqual(20, len(matches))

    def test_search_with_results_and_offset(self):
        matches = self.search_service.search('bug', start=20)
        self.assertEqual(20, matches.start)
        self.assertEqual(25, matches.total)
        self.assertEqual(5, len(matches))
        self.assertEqual([
            'http://bugs.launchpad.dev/ubuntu/hoary/+bug/2',
            'http://bugs.launchpad.dev/debian/+source/mozilla-firefox/+bug/2',
            'http://bugs.launchpad.dev/debian/+source/mozilla-firefox/+bug/3',
            'http://bugs.launchpad.dev/bugs/bugtrackers',
            'http://bugs.launchpad.dev/bugs/bugtrackers/debbugs'],
            [match.url for match in matches])

    def test_search_no_results(self):
        matches = self.search_service.search('fnord')
        self.assertEqual(0, matches.start)
        self.assertEqual(0, matches.total)
        self.assertEqual(0, len(matches))

    def test_search_no_meaningful_results(self):
        matches = self.search_service.search('no-meaningful')
        self.assertEqual(0, matches.start)
        self.assertEqual(1, matches.total)
        self.assertEqual(0, len(matches))

    def test_search_incomplete_response(self):
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service.search, 'gnomebaker')

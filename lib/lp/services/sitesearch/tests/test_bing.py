# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the bing search service."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import json
import os.path
import re

from fixtures import MockPatch
from requests import Response
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    )
import responses
from testtools.matchers import (
    ContainsDict,
    Equals,
    HasLength,
    MatchesListwise,
    MatchesStructure,
    )

from lp.services.config import config
from lp.services.sitesearch import BingSearchService
from lp.services.sitesearch.interfaces import SiteSearchResponseError
from lp.services.timeout import TimeoutError
from lp.testing import TestCase
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import BingLaunchpadFunctionalLayer


class TestBingSearchService(TestCase):
    """Test BingSearchService."""

    layer = BingLaunchpadFunctionalLayer

    def setUp(self):
        super(TestBingSearchService, self).setUp()
        self.search_service = BingSearchService()
        self.base_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), 'data'))
        self.pushConfig('launchpad', http_proxy='none')

    def test_configuration(self):
        self.assertEqual(config.bing.site, self.search_service.site)
        self.assertEqual(
            config.bing.subscription_key, self.search_service.subscription_key)
        self.assertEqual(
            config.bing.custom_config_id, self.search_service.custom_config_id)

    def test_create_search_url(self):
        self.assertEndsWith(
            self.search_service.create_search_url(terms='svg +bugs'),
            '&offset=0&q=svg+%2Bbugs')

    def test_create_search_url_escapes_unicode_chars(self):
        self.assertEndsWith(
            self.search_service.create_search_url(
                'Carlos Perell\xf3 Mar\xedn'),
            '&offset=0&q=Carlos+Perell%C3%B3+Mar%C3%ADn')

    def test_create_search_url_with_offset(self):
        self.assertEndsWith(
            self.search_service.create_search_url(terms='svg +bugs', start=20),
            '&offset=20&q=svg+%2Bbugs')

    def test_create_search_url_empty_terms(self):
        self.assertRaisesWithContent(
            ValueError, "Missing value for parameter 'q'.",
            self.search_service.create_search_url, '')

    def test_create_search_url_null_terms(self):
        self.assertRaisesWithContent(
            ValueError, "Missing value for parameter 'q'.",
            self.search_service.create_search_url, None)

    def test_create_search_url_requires_start(self):
        self.assertRaisesWithContent(
            ValueError, "Value for parameter 'offset' is not an int.",
            self.search_service.create_search_url, 'bugs', 'true')

    def test_parse_search_response_invalid_total(self):
        """The PageMatches's total attribute comes from the
        `webPages.totalEstimatedMatches` JSON element.
        When it cannot be found and the value cast to an int,
        an error is raised. If Bing were to redefine the meaning of the
        element to use a '~' to indicate an approximate total, an error would
        be raised.
        """
        file_name = os.path.join(
            self.base_path, 'bingsearchservice-incompatible-matches.json')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        self.assertEqual(
            '~25', json.loads(response)['webPages']['totalEstimatedMatches'])

        self.assertRaisesWithContent(
            SiteSearchResponseError,
            "Could not get the total from the Bing JSON response.",
            self.search_service._parse_search_response, response)

    def test_parse_search_response_negative_total(self):
        """If the total is ever less than zero (see bug 683115),
        this is expected: we simply return a total of 0.
        """
        file_name = os.path.join(
            self.base_path, 'bingsearchservice-negative-total.json')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        self.assertEqual(
            -25, json.loads(response)['webPages']['totalEstimatedMatches'])

        matches = self.search_service._parse_search_response(response)
        self.assertEqual(0, matches.total)

    def test_parse_search_response_missing_title(self):
        """A PageMatch requires a title, url, and a summary. If those elements
        cannot be found, a PageMatch cannot be made. A missing title ('name')
        indicates a bad page on Launchpad, so it is ignored. In this example,
        the first match is missing a title, so only the second page is present
        in the PageMatches.
        """
        file_name = os.path.join(
            self.base_path, 'bingsearchservice-missing-title.json')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        self.assertThat(
            json.loads(response)['webPages']['value'], HasLength(2))

        matches = self.search_service._parse_search_response(response)
        self.assertThat(matches, MatchesListwise([
            MatchesStructure.byEquality(
                title='GCleaner in Launchpad',
                url='http://launchpad.dev/gcleaner'),
            ]))

    def test_parse_search_response_missing_summary(self):
        """When a match is missing a summary ('snippet'), the match is skipped
        because there is no information about why it matched. This appears to
        relate to pages that are in the index, but should be removed. In this
        example taken from real data, the links are to the same page on
        different vhosts. The edge vhost has no summary, so it is skipped.
        """
        file_name = os.path.join(
            self.base_path, 'bingsearchservice-missing-summary.json')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        self.assertThat(
            json.loads(response)['webPages']['value'], HasLength(2))

        matches = self.search_service._parse_search_response(response)
        self.assertThat(matches, MatchesListwise([
            MatchesStructure.byEquality(
                title='BugExpiry - Launchpad Help',
                url='https://help.launchpad.net/BugExpiry'),
            ]))

    def test_parse_search_response_missing_url(self):
        """When the URL ('url') cannot be found the match is skipped. There are
        no examples of this. We do not want this hypothetical situation to give
        users a bad experience.
        """
        file_name = os.path.join(
            self.base_path, 'bingsearchservice-missing-url.json')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        self.assertThat(
            json.loads(response)['webPages']['value'], HasLength(2))

        matches = self.search_service._parse_search_response(response)
        self.assertThat(matches, MatchesListwise([
            MatchesStructure.byEquality(
                title='LongoMatch in Launchpad',
                url='http://launchpad.dev/longomatch'),
            ]))

    def test_parse_search_response_with_no_meaningful_results(self):
        """If no matches are found in the response, and there are 20 or fewer
        results, an Empty PageMatches is returned. This happens when the
        results are missing titles and summaries. This is not considered to be
        a problem because the small number implies that Bing did a poor job
        of indexing pages or indexed the wrong Launchpad server. In this
        example, there is only one match, but the results is missing a title so
        there is not enough information to make a PageMatch.
        """
        file_name = os.path.join(
            self.base_path, 'bingsearchservice-no-meaningful-results.json')
        with open(file_name, 'r') as response_file:
            response = response_file.read()
        self.assertThat(
            json.loads(response)['webPages']['value'], HasLength(1))

        matches = self.search_service._parse_search_response(response)
        self.assertThat(matches, HasLength(0))

    @responses.activate
    def test_search_converts_HTTPError(self):
        # The method converts HTTPError to SiteSearchResponseError.
        args = ('url', 500, 'oops', {}, None)
        responses.add('GET', re.compile(r'.*'), body=HTTPError(*args))
        self.assertRaises(
            SiteSearchResponseError, self.search_service.search, 'fnord')

    @responses.activate
    def test_search_converts_ConnectionError(self):
        # The method converts ConnectionError to SiteSearchResponseError.
        responses.add('GET', re.compile(r'.*'), body=ConnectionError('oops'))
        self.assertRaises(
            SiteSearchResponseError, self.search_service.search, 'fnord')

    @responses.activate
    def test_search_converts_TimeoutError(self):
        # The method converts TimeoutError to SiteSearchResponseError.
        responses.add('GET', re.compile(r'.*'), body=TimeoutError('oops'))
        self.assertRaises(
            SiteSearchResponseError, self.search_service.search, 'fnord')

    def test_parse_search_response_TypeError(self):
        # The method converts TypeError to SiteSearchResponseError.
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service._parse_search_response, None)

    def test_parse_search_response_ValueError(self):
        # The method converts ValueError to SiteSearchResponseError.
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service._parse_search_response, '')

    def test_parse_search_response_KeyError(self):
        # The method converts KeyError to SiteSearchResponseError.
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service._parse_search_response, '{}')

    def test_search_uses_proxy(self):
        proxy = 'http://proxy.example:3128/'
        self.pushConfig('launchpad', http_proxy=proxy)
        fake_send = FakeMethod(result=Response())
        self.useFixture(
            MockPatch('requests.adapters.HTTPAdapter.send', fake_send))
        # Our mock doesn't return a valid response, but we don't care; we
        # only care about how the adapter is called.
        self.assertRaises(
            SiteSearchResponseError, self.search_service.search, 'fnord')
        self.assertThat(
            fake_send.calls[0][1]['proxies'],
            ContainsDict({
                scheme: Equals(proxy) for scheme in ('http', 'https')
                }))

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
        self.assertEqual(25, matches.total)
        self.assertEqual(0, len(matches))

    def test_search_incomplete_response(self):
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service.search, 'gnomebaker')

    def test_search_error_response(self):
        self.assertRaises(
            SiteSearchResponseError,
            self.search_service.search, 'errors-please')

    def test_search_xss(self):
        matches = self.search_service.search('xss')
        self.assertThat(matches[0], MatchesStructure.byEquality(
            url='http://bugs.launchpad.dev/horizon/+bug/1349491',
            title=(
                'Bug #1349491 \u201c[OSSA 2014-027] Persistent &lt;XSS&gt; in '
                'the Host Aggrega...\u201d : Bugs ...'),
            summary=(
                '* Enter some name and an availability zone like this: '
                '&lt;svg onload=alert(1)&gt; * Save ... - Persistent XSS in '
                'the Host Aggregates interface (CVE-2014-3594) + ...')))

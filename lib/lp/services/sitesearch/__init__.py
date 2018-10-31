# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for searching and working with results."""

__metaclass__ = type

__all__ = [
    'BingSearchService',
    'PageMatch',
    'PageMatches',
    ]

import json
import urllib
from urlparse import (
    parse_qsl,
    urlunparse,
    )

from lazr.restful.utils import get_current_browser_request
from lazr.uri import URI
import requests
from zope.interface import implementer

from lp.services.config import config
from lp.services.sitesearch.interfaces import (
    ISearchResult,
    ISearchResults,
    ISearchService,
    SiteSearchResponseError,
    )
from lp.services.timeline.requesttimeline import get_request_timeline
from lp.services.timeout import (
    TimeoutError,
    urlfetch,
    )
from lp.services.webapp import urlparse
from lp.services.webapp.escaping import structured


@implementer(ISearchResult)
class PageMatch:
    """See `ISearchResult`.

    A search result that represents a web page.
    """

    @property
    def url_rewrite_exceptions(self):
        """A list of launchpad.net URLs that must not be rewritten.

        Configured in config.sitesearch.url_rewrite_exceptions.
        """
        return config.sitesearch.url_rewrite_exceptions.split()

    @property
    def url_rewrite_scheme(self):
        """The URL scheme used in rewritten URLs.

        Configured in config.vhosts.use_https.
        """
        if config.vhosts.use_https:
            return 'https'
        else:
            return 'http'

    @property
    def url_rewrite_hostname(self):
        """The network location used in rewritten URLs.

        Configured in config.vhost.mainsite.hostname.
        """
        return config.vhost.mainsite.hostname

    def __init__(self, title, url, summary):
        """initialize a PageMatch.

        :param title: A string. The title of the item.
        :param url: A string. The full URL of the item.
        :param summary: A string. A summary of the item.
        """
        self.title = title
        self.summary = summary
        self.url = self._rewrite_url(url)

    def _sanitize_query_string(self, url):
        """Escapes invalid urls."""
        parts = urlparse(url)
        querydata = parse_qsl(parts.query)
        querystring = urllib.urlencode(querydata)
        urldata = list(parts)
        urldata[-2] = querystring
        return urlunparse(urldata)

    def _strip_trailing_slash(self, url):
        """Return the url without a trailing slash."""
        uri = URI(url).ensureNoSlash()
        return str(uri)

    def _rewrite_url(self, url):
        """Rewrite the url to the local environment.

        Links with launchpad.net are rewritten to the local hostname,
        except if the domain matches a domain in the url_rewrite_exceptions.
        property.

        :param url: A URL str that may be rewritten to the local
            launchpad environment.
        :return: A URL str.
        """
        url = self._sanitize_query_string(url)
        if self.url_rewrite_hostname == 'launchpad.net':
            # Do not rewrite the url is the hostname is the public hostname.
            return self._strip_trailing_slash(url)
        parts = urlparse(url)
        for netloc in self.url_rewrite_exceptions:
            # The network location is parts[1] in the tuple.
            if netloc in parts[1]:
                return url
        local_scheme = self.url_rewrite_scheme
        local_hostname = parts[1].replace(
            'launchpad.net', self.url_rewrite_hostname)
        local_parts = tuple(
            [local_scheme] + [local_hostname] + list(parts[2:]))
        url = urlunparse(local_parts)
        return self._strip_trailing_slash(url)


@implementer(ISearchResults)
class PageMatches:
    """See `ISearchResults`.

    A collection of PageMatches.
    """

    def __init__(self, matches, start, total):
        """initialize a PageMatches.

        :param matches: A list of `PageMatch` objects.
        :param start: The index of the first item in the collection relative
            to the total number of items.
        :param total: The total number of items that matched a search.
        """
        self._matches = matches
        self.start = start
        self.total = total

    def __len__(self):
        """See `ISearchResults`."""
        return len(self._matches)

    def __getitem__(self, index):
        """See `ISearchResults`."""
        return self._matches[index]

    def __iter__(self):
        """See `ISearchResults`."""
        return iter(self._matches)


@implementer(ISearchService)
class BingSearchService:
    """See `ISearchService`.

    A search service that searches Bing for launchpad.net pages.
    """

    _default_values = {
        # XXX: maxiberta 2018-03-26: Set `mkt` based on the current request.
        'customConfig': None,
        'mkt': 'en-US',
        'count': 20,
        'offset': 0,
        'q': None,
        }

    @property
    def subscription_key(self):
        """The subscription key issued by Bing Custom Search."""
        return config.bing.subscription_key

    @property
    def custom_config_id(self):
        """The custom search instance as configured in Bing Custom Search."""
        return config.bing.custom_config_id

    @property
    def site(self):
        """The URL to the Bing Custom Search service.

        The URL is probably
        https://api.cognitive.microsoft.com/bingcustomsearch/v7.0/search.
        """
        return config.bing.site

    def search(self, terms, start=0):
        """See `ISearchService`.

        The `subscription_key` and `custom_config_id` are used in the
        search request. Search returns 20 or fewer results for each query.
        For terms that match more than 20 results, the start param can be
        used over multiple queries to get successive sets of results.

        :return: `ISearchResults` (PageMatches).
        :raise: `SiteSearchResponseError` if the json response is incomplete or
            cannot be parsed.
        """
        search_url = self.create_search_url(terms, start=start)
        search_headers = self.create_search_headers()
        request = get_current_browser_request()
        timeline = get_request_timeline(request)
        action = timeline.start("bing-search-api", search_url)
        try:
            response = urlfetch(
                search_url, headers=search_headers, use_proxy=True)
        except (TimeoutError, requests.RequestException) as error:
            raise SiteSearchResponseError(
                "The response errored: %s" % str(error))
        finally:
            action.finish()
        page_matches = self._parse_search_response(response.content, start)
        return page_matches

    def _checkParameter(self, name, value, is_int=False):
        """Check that a parameter value is not None or an empty string."""
        if value in (None, ''):
            raise ValueError("Missing value for parameter '%s'." % name)
        if is_int:
            try:
                int(value)
            except ValueError:
                raise ValueError(
                    "Value for parameter '%s' is not an int." % name)

    def create_search_url(self, terms, start=0):
        """Return a Bing Custom Search search url."""
        self._checkParameter('q', terms)
        self._checkParameter('offset', start, is_int=True)
        self._checkParameter('customConfig', self.custom_config_id)
        search_params = dict(self._default_values)
        search_params['q'] = terms.encode('utf8')
        search_params['offset'] = start
        search_params['customConfig'] = self.custom_config_id
        query_string = urllib.urlencode(sorted(search_params.items()))
        return self.site + '?' + query_string

    def create_search_headers(self):
        """Return a dict with Bing Custom Search compatible request headers."""
        self._checkParameter('subscription_key', self.subscription_key)
        return {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            }

    def _parse_search_response(self, bing_json, start=0):
        """Return a `PageMatches` object.

        :param bing_json: A string containing Bing Custom Search API v7 JSON.
        :return: `ISearchResults` (PageMatches).
        :raise: `SiteSearchResponseError` if the json response is incomplete or
            cannot be parsed.
        """
        try:
            bing_doc = json.loads(bing_json)
        except (TypeError, ValueError):
            raise SiteSearchResponseError(
                "The response was incomplete, no JSON.")

        try:
            response_type = bing_doc['_type']
        except (AttributeError, KeyError, ValueError):
            raise SiteSearchResponseError(
                "Could not get the '_type' from the Bing JSON response.")

        if response_type == 'ErrorResponse':
            try:
                errors = [error['message'] for error in bing_doc['errors']]
                raise SiteSearchResponseError(
                    "Error response from Bing: %s" % '; '.join(errors))
            except (AttributeError, KeyError, TypeError, ValueError):
                raise SiteSearchResponseError(
                    "Unable to parse the Bing JSON error response.")
        elif response_type != 'SearchResponse':
            raise SiteSearchResponseError(
                "Unknown Bing JSON response type: '%s'." % response_type)

        page_matches = []
        total = 0
        try:
            results = bing_doc['webPages']['value']
        except (AttributeError, KeyError, ValueError):
            # Bing did not match any pages. Return an empty PageMatches.
            return PageMatches(page_matches, start, total)

        try:
            total = int(bing_doc['webPages']['totalEstimatedMatches'])
        except (AttributeError, KeyError, ValueError):
            # The datatype is not what PageMatches requires.
            raise SiteSearchResponseError(
                "Could not get the total from the Bing JSON response.")
        if total < 0:
            # See bug 683115.
            total = 0
        for result in results:
            url = result.get('url')
            title = result.get('name')
            summary = result.get('snippet')
            if None in (url, title, summary):
                # There is not enough data to create a PageMatch object.
                # This can be caused by an empty title or summary which
                # has been observed for pages that are from vhosts that
                # should not be indexed.
                continue
            summary = summary.replace('<br>', '')
            # Strings in Bing's search results are unescaped by default.  We
            # could alternatively fix this by sending textFormat=HTML, but
            # let's just do our own escaping for now.
            title = structured('%s', title).escapedtext
            summary = structured('%s', summary).escapedtext
            page_matches.append(PageMatch(title, url, summary))

        return PageMatches(page_matches, start, total)

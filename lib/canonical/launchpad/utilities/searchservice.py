# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for searching and working with results."""

__metaclass__ = type

__all__ = [
    'GoogleSearchService',
    'PageMatch',
    'PageMatches',
    ]

import cElementTree as ET
import urllib
from urlparse import urlunparse

from zope.interface import implements

from canonical.config import config
from canonical.launchpad.interfaces.searchservice import (
    ISearchResult, ISearchResults, ISearchService, GoogleParamError,
    GoogleWrongGSPVersion)
from canonical.launchpad.webapp import urlparse


class PageMatch:
    """See `ISearchResult`.

    A search result that represents a web page.
    """
    implements(ISearchResult)

    @property
    def url_rewrite_exceptions(self):
        """A list of launchpad.net URLs that must not be rewritten.

        Configured in config.google.url_rewrite_exceptions.
        """
        return config.google.url_rewrite_exceptions.split()

    @property
    def url_rewrite_scheme(self):
        """The URL scheme used in rewritten URLs.

        Configured in config.google.url_rewrite_scheme.
        """
        return config.google.url_rewrite_scheme

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

    def _rewrite_url(self, url):
        """Rewrite the url to the local environment.

        Links with launhcpad.net are rewritten to the local hostname,
        except if the domain matches a domain in the
        config.url_rewrite_exceptions.

        :param url: A url str that may be rewritten to the local
            launchpad environment.
        :return: A url str.
        """
        if self.url_rewrite_hostname == 'launchpad.net':
            # Do not rewrite the url is the hostname is the public hostname.
            return url
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
        return urlunparse(local_parts)


class PageMatches:
    """See `ISearchResults`.

    A collection of PageMatches.
    """
    implements(ISearchResults)

    def __init__(self, matches, start, total):
        """initialize a PageMatches.

        :param matches: A list of `PageMatch` objects.
        :param start: The index of the first item in the collection relative
            to the total number of items.
        :param total: The total number of items that matched a search.
        """
        self._matches = matches
        self._start = start
        self._total = total

    @property
    def start(self):
        """See `ISearchResults`."""
        return self._start

    @property
    def total(self):
        """See `ISearchResults`."""
        return self._total

    def __len__(self):
        """See `ISearchResults`."""
        return len(self._matches)

    def __getitem__(self, index):
        """See `ISearchResults`."""
        return self._matches[index]

    def __iter__(self):
        """See `ISearchResults`."""
        for match in self._matches:
            yield match


class GoogleSearchService:
    """See `ISearchService`.

    A search service that search Google for launchpad.net pages.
    """
    implements(ISearchService)

    _default_values = {
        'as_rq' : 'launchpad.net',
        'client' : 'google-csbe',
        'cx' : None,
        'ie' : 'utf8',
        'num' : 20,
        'oe' : 'utf8',
        'output' : 'xml_no_dtd',
        'start': 0,
        'q' : None,
        }

    @property
    def client_id(self):
        """The client-id issued by Google.

        Google requires that each client of the Google Search Enging
        service to pass its id as a parameter in the request URL.
        """
        return config.google.client_id

    @property
    def site(self):
        """The URL to the Google Search Engine service.

        The URL is probably http://www.google.com/search.
        """
        return config.google.site

    def search(self, terms, start=0):
        """See `ISearchService`.

        The config.google.client_id is used as Google client-id in the
        search request. Search returns 20 or fewer results for each query.
        For terms that return more than 20 results, the start param can be
        used over multiple queries to get successive sets of results.

        :return: `ISearchResults` (PageMatches).
        :raise: `GoogleParamError` when an search parameter is None.
        :raise: `GoogleWrongGSPVersion` if the xml cannot be parsed.
        """
        search_url = self.create_search_url(terms, start=start)
        # XXX sinzui 2008-05-14: finish this.
        #response = urlopen(search_url)
        #gsp_xml = response.read()
        gsp_xml = ("""<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <GSP VER="3.2">
              <TM>0.123456</TM>
              <Q>svg +bugs</Q>
              <RES SN="1" EN="1">
                <M>1</M>
                <R N="1">
                    <U>http://bugs.launchpad.dev/firefox/+bug/1</U>
                    <T>SVG is broken in Firefox</T>
                    <S>This matches because <b>svg</b> is in the title.</S>
                </R>
              </RES>
            </GSP>
            """.encode('utf8'))
        page_matches = self._parse_google_search_protocol(gsp_xml)
        return page_matches

    def _checkParameter(self, name, value):
        """Check that a parameter value is not None or and empty string."""
        if value in (None, ''):
            raise GoogleParamError("Parameters must have values: %s." % name)

    def create_search_url(self, terms, start=0):
        """Return a Google search url."""
        self._checkParameter('q', terms)
        safe_terms = urllib.quote_plus(terms.encode('utf8'))
        search_params = dict(self._default_values)
        search_params['q'] = safe_terms
        search_params['start'] = start
        search_params['cx'] = self.client_id
        search_param_list = []
        for name in sorted(search_params):
            value = search_params[name]
            self._checkParameter(name, value)
            search_param_list.append('%s=%s' % (name, value))
        query_string = '&'.join(search_param_list)
        return config.google.site + '?' + query_string

    def _parse_google_search_protocol(self, gsp_xml):
        """Return a `PageMatches` object.

        :param gsp_xml: A string that must be Google Search Protocol
            version 3.2 XML. There is no guarantee that other GSP versions
            can be parsed.
        :return: `ISearchResults` (PageMatches).
        :raise: `GoogleWrongGSPVersion` if the xml cannot be parsed.
        """
        error_message =  "The xml is not Google Search Protocol version 3.2."
        gsp_doc = ET.fromstring(gsp_xml)
        results = gsp_doc.find('RES')
        try:
            start = int(results.get('SN'))
            total = int(results.find('M').text)
        except (AttributeError, ValueError):
            # The datatype is not what PageMatches requires.
            raise GoogleWrongGSPVersion(error_message)
        page_matches = []
        for result in results.findall('R'):
            title = result.find('T').text
            url = result.find('U').text
            summary = result.find('S').text
            if None in (title, url, summary):
                # There is not enough data to create a PageMatch object.
                raise GoogleWrongGSPVersion(error_message)
            page_matches.append(PageMatch(title, url, summary))
        return PageMatches(page_matches, start, total)

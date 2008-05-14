# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for searching and working with results."""

__metaclass__ = type

__all__ = [
    'GoogleSearchService',
    'PageMatch',
    'PageMatches',
    ]

import urllib

from zope.interface import implements

from canonical.launchpad.interfaces.searchservice import (
    ISearchResult, ISearchResults, ISearchService, GoogleParamError)


class PageMatch:
    """See `ISearchResult`.

    A search result that represents a web page.
    """
    implements(ISearchResult)

    def __init__(self, title, url, description):
        """initialize a PageMatch.

        :param title: A string. The title of the item.
        :param url: A string. The full URL of the item.
        :param description: A string. A description of the item.
        """
        self.title = title
        self.description = description
        self.url = self._rewrite_url(url)

    def _rewrite_url(self, url):
        """Rewrite the url to the local environment.

        Links with launhcpad.net are rewritten to config.vhost.mainsite,
        except if the domain matches a domain in the
        config.url_rewrite_exceptions

        :param url: A url str that may be rewritten to the local
            launchpad environment.
        :return: A url str.
        """
        # XXX sinzui 2008-05-13: finish this


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

    def __len__(self):
        """See `ISearchResults`."""

    def __getitem__(self, index):
        """See `ISearchResults`."""

    def __iter__(self):
        """See `ISearchResults`."""


class GoogleSearchService:
    """See ISearchService.

    A search service that search google for launchpad.net pages.
    """
    implements(ISearchService)

    _default_values = {
        'as_rq' : 'launchpad.net',
        'client' : 'google-csbe',
        'client-id' : None,
        'ie' : 'utf8',
        'num' : 20,
        'oe' : 'utf8',
        'output' : 'xml_no_dtd',
        'start': 0,
        'q' : None,
        }

    def search(terms, start=None):
        """See ISearchService.

        The config.google.client_id is used as Google client-id in the
        search request. Search returns 20 or fewer results for each query.
        For terms that return more than 20 results, the start param can be
        used over multiple queries to get successive sets of results.
        
        :return: ISearchResults (PageMatches).
        :raises: GoogleParamError when an search parameter is None.
        """
        search_url = self.create_search_url(terms, start=start)
        XXX sinzui 2008-05-14: finish this

    def create_search_url(terms, start=None):
        """Return a Google search url."""
        search_params = dict(self._default_values)
        if start is not None:
            search_params['start'] = start
        safe_terms = urllib.quote_plus(terms.encode('utf8'))
        search_params['q'] = safe_terms
        search_param_list = []
        for key in sorted(google_search._default_values):
            value =  google_search._default_values[key]
            if value is None:
                raise GoogleParamError(
                    "Parameters cannot be None: %s." % key)
            search_param_list.append('%s=%s', (key, value))
        query_string '&'.join(search_param_list)
        return config.google.site + '?' + query_string

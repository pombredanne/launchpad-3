# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for searching and working with results."""

__metaclass__ = type

__all__ = [
    'ISearchResult',
    'ISearchResults',
    'ISearchService',
    'GoogleParamError',
    ]

from zope.interface import Interface, Attribute


class ISearchResult:
    """An item that matches a search query."""

    title = Attribute('The title of the item.')
    url = Attribute('The full URL of the item.')
    description = Attribute(
        'A description of the item, possibly with information about why '
        'the item is considered to be a valid result for a search.')


class ISearchResults:
    """A collection of `ISearchResult` items that match a search query."""

    total = Attribute('The total number of items that matched a search.')
    start = Attribute(
        'The index of the first item in the collection relative to the '
        'total number of items. The collection may only contain a slice '
        'of the total search results.')

    def __len__():
        """The number of items in the collection returned by the search."""

    def __getitem__(index):
        """Return the item at index in the collection."""

    def __iter__():
        """Iterate over the items in the collection."""


class GoogleParamError(ValueError):
    """Raise when a Google search parameter has a bad value."""


class ISearchService:
    """A service that can return an `ISearchResults` for a query."""

    def search(terms, start=0):
        """Search a source for items that match the terms and.

        :param terms: A string of terms understood by the search service.
        :param start: The index of the first item to return in the 
            `ISearchResults` collection. The search service may limit the
            number of items in the results. The start parameter can be used
            to page though batches of `ISearchResults`.
        :return: `ISearchResults`.
        """

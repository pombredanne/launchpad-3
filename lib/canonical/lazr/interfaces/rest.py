# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces for different kinds of HTTP resources."""

__metaclass__ = type
__all__ = [
    'ICollectionResource',
    'IEntryResource',
    'IHTTPResource',
    'IJSONPublishable'
    ]

from zope.interface import Interface
from zope.publisher.interfaces import IPublishTraverse


class IHTTPResource(IPublishTraverse):
    """An object published through HTTP."""

    def __call__(self, REQUEST=None):
        """Publish the object."""


class IJSONPublishable(Interface):
    """An object that can be published as a JSON data structure."""

    def toJSONReady(self):
        """Return a JSON-ready representation of this object.

        The object must consist entirely of simple data structures and
        IJSONPublishable objects.
        """


class IEntryResource(IHTTPResource, IJSONPublishable):
    """A resource that represents an individual Launchpad object."""
    def get(self):
        """Retrieve this object.

        :return: A string representation.
        """


class ICollectionResource(IHTTPResource):
    """A resource that represents a collection of entry resources."""

    def lookupEntry(self, request, name):
        """Look up an entry in the collection by unique identifier.

        :return: An IEntryResource
        """

    def get(self):
        """Retrieve this collection.

        :return: A string representation.
        """

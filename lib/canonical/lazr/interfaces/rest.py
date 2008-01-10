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

    def __init__(self, request):
        """Associate the object with an incoming request."""

    def __call__(self):
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
    def do_GET(self):
        """Retrieve this object.

        :return: A string representation.
        """


class ICollectionResource(IHTTPResource):
    """A resource that represents a collection of entry resources."""

    def do_GET(self):
        """Retrieve this collection.

        :return: A string representation.
        """

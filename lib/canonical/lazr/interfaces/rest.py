# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces for different kinds of HTTP resources."""

__metaclass__ = type
__all__ = [
    'IHTTPResource',
    ]

from zope.interface import Interface


class IHTTPResource(Interface):
    """An object published through HTTP."""

    def __call__(self):
        """Publish this resource to the web."""


class IJSONPublishable(Interface):
    """An object that can be published as a JSON data structure."""

    def toJSON(self):
        """Return a JSON representation of this object."""


class IEntryResource(IJSONPublishable):
    """A resource that represents an individual Launchpad object."""
    def get(self):
        """Retrieve this object.

        :return: A string representation.
        """


class ICollectionResource(Interface):
    """A resource that represents a collection of entry resources."""

    def get(self):
        """Retrieve this collection.

        :return: A string representation.
        """

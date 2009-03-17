# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Data model objects for the LAZR example web service."""

__metaclass__ = type
__all__ = ['Cookbook',
           'CookbookServiceRootResource',
           'CookbookSet',
           'CookbookWebServiceObject',
           'CookbookServiceRootAbsoluteURL']

from zope.interface import implements
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.component import adapts, getUtility
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from canonical.lazr.rest import ServiceRootResource
from canonical.lazr.interfaces.rest import (
    IServiceRootResource, IWebServiceConfiguration)
from canonical.lazr.rest.example.interfaces import (
    ICookbook, ICookbookSet, IHasGet)


class CookbookWebServiceObject:
    """A basic object published through the web service."""


class CookbookTopLevelObject(CookbookWebServiceObject):
    """An object published at the top level of the web service."""

    @property
    def __parent__(self):
        return getUtility(IServiceRootResource)

    @property
    def __name__(self):
        raise NotImplementedError()


class Cookbook(CookbookWebServiceObject):
    """An object representing a cookbook"""
    implements(ICookbook, IAbsoluteURL)
    def __init__(self, name):
        self.name = name

    @property
    def __name__(self):
        return self.name


# Define some globally accessible sample data.
C1 = Cookbook(u"Mastering the Art of French Cooking")
C2 = Cookbook(u"The Joy of Cooking")
C3 = Cookbook(u"James Beard's American Cookery")
COOKBOOKS = [C1, C2, C3]


class CookbookSet(CookbookTopLevelObject):
    """The set of all cookbooks."""
    implements(ICookbookSet)

    def __init__(self, cookbooks=None):
        if cookbooks is None:
            cookbooks = COOKBOOKS
        self.cookbooks = list(cookbooks)

    def getCookbooks(self):
        return self.cookbooks

    def get(self, name):
        match = [c for c in self.cookbooks if c.name == name]
        if len(match) > 0:
            return match[0]
        return None

    __name__ = "cookbooks"


class CookbookServiceRootResource(ServiceRootResource):
    """A service root for the cookbook web service.

    Traversal to top-level resources is handled with the get() method.
    The top-level objects are stored in the top_level_names dict.
    """
    implements(IHasGet)

    @property
    def top_level_names(self):
        """Access or create the list of top-level objects."""
        return {'cookbooks': getUtility(ICookbookSet)}

    def get(self, name):
        """Traverse to a top-level object."""
        obj = self.top_level_names.get(name)
        obj.__parent__ = self
        return obj


class CookbookServiceRootAbsoluteURL:
    """A basic implementation of IAbsoluteURL for the root object."""
    implements(IAbsoluteURL)
    adapts(CookbookServiceRootResource, IDefaultBrowserLayer)

    HOSTNAME = "http://api.cookbooks.dev/"

    def __init__(self, context, request):
        """Initialize with respect to a context and request."""
        self.version = getUtility(
            IWebServiceConfiguration).service_version_uri_prefix

    def __str__(self):
        """Return the semi-hard-coded URL to the service root."""
        return self.HOSTNAME + self.version

    __call__ = __str__

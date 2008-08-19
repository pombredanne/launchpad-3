# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Classes for creating navigation breadcrumbs."""

__metaclass__ = type

__all__ = [
    'Breadcrumb',
    'BreadcrumbBuilder',
    ]


from zope.interface import implements

from canonical.launchpad.webapp.interfaces import (
    IBreadcrumb, IBreadcrumbBuilder)


class Breadcrumb:
    """See `IBreadcrumb`."""
    implements(IBreadcrumb)

    def __init__(self, url, text):
        self.url = url
        self.text = text

    def __repr__(self):
        return "<%s url='%s' text='%s'>" % (
            self.__class__.__name__, self.url, self.text)


class BreadcrumbBuilder:
    """See `IBreadcrumbBuilder`.

    This class is intended for use as an adapter.
    """
    implements(IBreadcrumbBuilder)

    text = None
    url = None

    def __init__(self, context):
        self.context = context

    def make_breadcrumb(self):
        """See `IBreadcrumbBuilder.`"""
        if self.text is None:
            raise AssertionError(
                "The builder has not been given valid text for the "
                "breadcrumb.")
        if self.url is None:
            raise AssertionError(
               "The builder has not been given a valid breadcrumb URL.")

        return Breadcrumb(self.url, self.text)

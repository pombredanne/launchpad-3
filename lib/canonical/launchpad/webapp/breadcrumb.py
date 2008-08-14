# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Classes for creating navigation breadcrumbs."""

__metaclass__ = type

__all__ = [
    'Breadcrumb',
    'BreadcrumbBuilder',
    ]


from zope.interface import implements

from canonical.launchpad.webapp.interfaces import (
    IBreadcrumb, IBreadcrumbBuilder, IncompleteBreadcrumbError)


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

    def __init__(self, context):
        self.context = context

    def _get_attribute(self, attrname):
        """Return the value of a possibly callable attribute."""
        attr = getattr(self, attrname, None)
        if attr is None:
            raise IncompleteBreadcrumbError(
                "No '%s' attribute was given with which to build the "
                "Breadcrumb object." % attrname)
        return attr

    def make_breadcrumb(self):
        url = self._get_attribute('url')
        text = self._get_attribute('text')
        return Breadcrumb(url, text)

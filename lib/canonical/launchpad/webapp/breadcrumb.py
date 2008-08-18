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

    def __init__(self, context):
        self.context = context
        # Storage for user-specified values.
        self._text = None
        self._url = None

    def _get_text(self):
        """Return the breadcrumb's 'text' attribute.  See `IBreadcrumb`."""
        if self._text is not None:
            return self._text
        raise NotImplementedError

    def _set_text(self, value):
        """Set the breadcrumb's 'text' attribute.  See `IBreadcrumb`."""
        self._text = value

    text = property(_get_text, _set_text, doc=_get_text.__doc__)

    def _get_url(self):
        """Return the breadcrumb's 'url' attribute.  See `IBreadcrumb`."""
        if self._url is not None:
            return self._url
        raise NotImplementedError

    def _set_url(self, value):
        """Set the breadcrumb's 'url' attribute.  See `IBreadcrumb`."""
        self._url = value

    url = property(_get_url, _set_url, doc=_get_url.__doc__)

    def make_breadcrumb(self):
        """See `IBreadcrumbBuilder.`"""
        return Breadcrumb(self.url, self.text)

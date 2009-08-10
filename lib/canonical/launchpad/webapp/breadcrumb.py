# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for creating navigation breadcrumbs."""

__metaclass__ = type

__all__ = [
    'Breadcrumb',
    'BreadcrumbBuilder',
    ]


from zope.traversing.interfaces import IPathAdapter
from zope.component import queryAdapter
from zope.interface import implements

from canonical.launchpad.webapp.interfaces import (
    IBreadcrumb, IBreadcrumbBuilder)


class Breadcrumb:
    """See `IBreadcrumb`."""
    implements(IBreadcrumb)

    def __init__(self, url, text, icon=None):
        self.url = url
        self.text = text
        self.icon = icon

    def __repr__(self):
        if self.icon is not None:
            icon_repr = " icon='%s'" % self.icon
        else:
            icon_repr = ""

        return "<%s url='%s' text='%s'%s>" % (
            self.__class__.__name__, self.url, self.text, icon_repr)


class BreadcrumbBuilder:
    """See `IBreadcrumbBuilder`.

    This class is intended for use as an adapter.
    """
    implements(IBreadcrumbBuilder)

    text = None
    url = None

    def __init__(self, context):
        self.context = context

    @property
    def icon(self):
        """See `IBreadcrumb`."""
        # Get the <img> tag from the path adapter.
        return queryAdapter(
            self.context, IPathAdapter, name='image').icon()

    def make_breadcrumb(self):
        """See `IBreadcrumbBuilder.`"""
        if self.text is None:
            raise AssertionError(
                "The builder has not been given valid text for the "
                "breadcrumb.")
        if self.url is None:
            raise AssertionError(
               "The builder has not been given a valid breadcrumb URL.")

        return Breadcrumb(self.url, self.text, icon=self.icon)

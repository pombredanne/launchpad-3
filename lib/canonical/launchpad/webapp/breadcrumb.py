# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Classes for creating navigation breadcrumbs."""

__metaclass__ = type

__all__ = [
    'Breadcrumb',
    'BreadcrumbBuilder',
    ]


from zope.interface import implements
from zope.component import queryAdapter

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
        self._icon = None
        self._icon_from_user = False

    def icon(self):
        """See `IBreadcrumb`."""
        if self._icon_from_user:
            return self._icon

        # FIXME: Yay for circular imports!
        from canonical.launchpad.interfaces.launchpad import IHasIcon
        if IHasIcon.providedBy(self.context):
            return self.context.icon
        else:
            return None

    def _set_icon(self, value):
        """Set the icon attribute and flag it as a user-defined value."""
        self._icon = value
        self._icon_from_user = True

    icon = property(icon, _set_icon, doc=icon.__doc__)

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

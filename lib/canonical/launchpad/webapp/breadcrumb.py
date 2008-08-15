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
    IBreadcrumb, IBreadcrumbBuilder, IncompleteBreadcrumbError)


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

    def __init__(self, context):
        self.context = context
        # Storage for user-assigned values.
        self._icon = None
        self._icon_from_user = False

    def _get_attribute(self, attrname):
        """Return the value of one of this class' attributes.

        :raises: `IncompleteBreadcrumbError` if the attribute is missing or
            None.
        """
        attr = getattr(self, attrname, None)
        if attr is None:
            raise IncompleteBreadcrumbError(
                "No '%s' attribute was given with which to build the "
                "Breadcrumb object." % attrname)
        return attr

    def _get_icon(self):
        """Return the icon URL for the builder's context.

        :returns: A URL, or None if the context doesn't have an icon.
        """
        if self._icon_from_user:
            return self._icon

        # FIXME: Yay for circular imports!
        from canonical.launchpad.interfaces.launchpad import IHasIcon
        if IHasIcon.providedBy(self.context):
            return self.context.icon
        else:
            return None

    def _set_icon(self, value):
        self._icon = value
        self._icon_from_user = True

    icon = property(_get_icon, _set_icon)

    def make_breadcrumb(self):
        url = self._get_attribute('url')
        text = self._get_attribute('text')
        return Breadcrumb(url, text, icon=self.icon)

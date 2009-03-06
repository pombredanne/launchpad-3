# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Views, menus and traversal related to PersonProducts."""

__metaclass__ = type
__all__ = []


from zope.component import queryAdapter
from zope.traversing.interfaces import IPathAdapter

from canonical.launchpad.interfaces.personproduct import IPersonProduct
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder
from canonical.launchpad.webapp import Navigation


class PersonProductNavigation(Navigation):
    """No-op navigation object."""
    usedfor = IPersonProduct


class PersonProductBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IPersonProduct`."""

    @property
    def text(self):
        return self.context.product.displayname

    @property
    def icon(self):
        return queryAdapter(
            self.context.product, IPathAdapter, name='image').icon()

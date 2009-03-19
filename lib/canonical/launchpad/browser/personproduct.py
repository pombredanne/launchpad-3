# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Views, menus and traversal related to PersonProducts."""

__metaclass__ = type
__all__ = [
    'PersonProductBreadcrumbBuilder',
    'PersonProductFacets',
    'PersonProductNavigation',
    ]


from zope.component import queryAdapter
from zope.traversing.interfaces import IPathAdapter

from canonical.launchpad.interfaces.personproduct import IPersonProduct
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder
from canonical.launchpad.webapp import (
    Link, Navigation, StandardLaunchpadFacets)
from canonical.launchpad.webapp.interfaces import NotFoundError


class PersonProductNavigation(Navigation):
    """No-op navigation object."""
    usedfor = IPersonProduct

    def traverse(self, path_segment):
        """Any traversal from here is not found."""
        raise NotFoundError


class PersonProductBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IPersonProduct`."""

    @property
    def text(self):
        return self.context.product.displayname

    @property
    def icon(self):
        return queryAdapter(
            self.context.product, IPathAdapter, name='image').icon()


class PersonProductFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IPerson."""

    usedfor = IPersonProduct

    enable_only = ['branches']

    def branches(self):
        text = 'Code'
        summary = ('Bazaar Branches of %s owned by %s' %
                   (self.context.product.displayname,
                    self.context.person.displayname))
        return Link('', text, summary)

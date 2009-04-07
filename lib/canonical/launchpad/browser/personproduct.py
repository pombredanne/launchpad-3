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

from canonical.launchpad.interfaces.branchnamespace import (
    get_branch_namespace)
from canonical.launchpad.interfaces.personproduct import IPersonProduct
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder
from canonical.launchpad.webapp import (
    Link, Navigation, StandardLaunchpadFacets)
from canonical.launchpad.webapp.interfaces import NotFoundError


class PersonProductNavigation(Navigation):
    """Navigation to branches for this person/product."""
    usedfor = IPersonProduct

    def traverse(self, branch_name):
        """Look for a branch in the person/product namespace."""
        namespace = get_branch_namespace(
            person=self.context.person, product=self.context.product)
        branch = namespace.getByName(branch_name)
        if branch is None:
            raise NotFoundError
        else:
            return branch


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

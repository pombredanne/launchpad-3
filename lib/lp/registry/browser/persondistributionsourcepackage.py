# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views, menus and traversal related to PersonDistributionSourcePackages."""

__metaclass__ = type
__all__ = [
    'PersonDistributionSourcePackageBreadcrumb',
    'PersonDistributionSourcePackageFacets',
    'PersonDistributionSourcePackageNavigation',
    ]


from zope.component import queryAdapter
from zope.interface import implementer
from zope.traversing.interfaces import IPathAdapter

from lp.app.errors import NotFoundError
from lp.code.browser.vcslisting import PersonTargetDefaultVCSNavigationMixin
from lp.registry.interfaces.persondistributionsourcepackage import (
    IPersonDistributionSourcePackage,
    )
from lp.services.webapp import (
    canonical_url,
    Navigation,
    StandardLaunchpadFacets,
    )
from lp.services.webapp.breadcrumb import Breadcrumb
from lp.services.webapp.interfaces import IMultiFacetedBreadcrumb


class PersonDistributionSourcePackageNavigation(
        PersonTargetDefaultVCSNavigationMixin, Navigation):
    usedfor = IPersonDistributionSourcePackage

    def traverse(self, branch_name):
        # XXX cjwatson 2015-02-06: This will look for Git repositories in
        # the person/DSP namespace, but for now it does nothing.
        raise NotFoundError


# XXX cjwatson 2015-01-29: Do we need two breadcrumbs, one for the
# distribution and one for the source package?
@implementer(IMultiFacetedBreadcrumb)
class PersonDistributionSourcePackageBreadcrumb(Breadcrumb):
    """Breadcrumb for an `IPersonDistributionSourcePackage`."""

    @property
    def text(self):
        return self.context.distro_source_package.displayname

    @property
    def url(self):
        if self._url is None:
            return canonical_url(
                self.context.distro_source_package, rootsite=self.rootsite)
        else:
            return self._url

    @property
    def icon(self):
        return queryAdapter(
            self.context.distro_source_package, IPathAdapter,
            name='image').icon()


class PersonDistributionSourcePackageFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IPersonDSP."""

    usedfor = IPersonDistributionSourcePackage
    enable_only = ['branches']

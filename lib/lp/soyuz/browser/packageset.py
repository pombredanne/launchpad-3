# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for packagesets."""

__metaclass__ = type

__all__ = [
    'PackagesetSetNavigation',
    ]

from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.webapp import GetitemNavigation
from lp.soyuz.interfaces.packageset import IPackagesetSet


class PackagesetSetNavigation(GetitemNavigation):
    """Navigation methods for PackagesetSet."""
    usedfor = IPackagesetSet

    def traverse(self, distribution_name):
        """Traverse package sets in distro series context.

        The URI fragment of interest is:

            /package-sets/ubuntu/lucid/mozilla

        where 'ubuntu' is the distro, 'lucid' is the distro series and
        'mozilla' is the package set.
        """
        distro = getUtility(IDistributionSet).getByName(distribution_name)
        if distro is None:
            return None
        if self.request.stepstogo:
            distroseries_name = self.request.stepstogo.consume()
            distroseries = distro[distroseries_name]
        if self.request.stepstogo:
            # The package set name follows after the distro series.
            ps_name = self.request.stepstogo.consume()
            return self.context.getByName(distroseries, ps_name)
        return None

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Retirement of packages that are removed upstream."""

__metaclass__ = type
__all__ = [
    'dominate_imported_source_packages',
    ]

from zope.component import getUtility

from lp.archivepublisher.domination import Dominator
from lp.registry.interfaces.distribution import IDistributionSet


def dominate_imported_source_packages(txn, logger, distro_name, series_name,
                                      pocket, packages_map):
    """Perform domination."""
    series = getUtility(IDistributionSet)[distro_name].getSeries(series_name)
    dominator = Dominator(logger, series.main_archive)

    # Dominate all packages published in the series.  This includes all
    # packages listed in the Sources file we imported, but also packages
    # that have been recently deleted.
    package_counts = dominator.findPublishedSourcePackageNames(series, pocket)
    for package_name, package_count in package_counts:
        entries = packages_map.src_map.get(package_name, [])
        live_versions = [
            entry['Version'] for entry in entries if 'Version' in entry]

        dominator.dominateRemovedSourceVersions(
            series, pocket, package_name, live_versions)

        txn.commit()

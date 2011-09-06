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


def dominate_imported_source_packages(logger, distro_name, series_name,
                                      pocket, packages_map):
    """Perform domination."""
    series = getUtility(IDistributionSet)[distro_name].getSeries(series_name)
    dominator = Dominator(logger, series.main_archive)
    for package_name, entries in packages_map.src_map.iteritems():
        live_versions = [
            entry['Version']
            for entry in entries if 'Version' in entry]
        dominator.dominateRemovedSourceVersions(
            series, pocket, package_name, live_versions)

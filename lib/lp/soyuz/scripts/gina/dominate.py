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

    # XXX JeroenVermeulen 2011-09-08, bug=844550: This is a transitional
    # hack.  Gina used to create SPPHs in Pending state.  We cleaned up
    # the bulk of them, and changed the code to create Published ones, but
    # some new ones will have been created since.
    # Update those to match what the new Gina does.
    from canonical.launchpad.interfaces.lpstorm import IStore
    from lp.soyuz.enums import PackagePublishingStatus
    from lp.soyuz.model.publishing import SourcePackagePublishingHistory
    SPPH = SourcePackagePublishingHistory
    store = IStore(SPPH)
    spphs = store.find(
        SPPH,
        SPPH.archive == series.main_archive,
        SPPH.distroseries == series,
        SPPH.pocket == pocket,
        SPPH.status == PackagePublishingStatus.PENDING)
    spphs.set(status=PackagePublishingStatus.PUBLISHED)

    # Dominate packages found in the Sources list we're importing.
    package_names = dominator.findPublishedSourcePackageNames(series, pocket)
    for package_name in package_names:
        entries = packages_map.src_map.get(package_name, [])
        live_versions = [
            entry['Version'] for entry in entries if 'Version' in entry]

        dominator.dominateRemovedSourceVersions(
            series, pocket, package_name, live_versions)

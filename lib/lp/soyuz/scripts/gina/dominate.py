# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Retirement of packages that are removed upstream."""

__metaclass__ = type
__all__ = [
    'dominate_imported_source_packages',
    ]

from zope.component import getUtility

# XXX JeroenVermeulen 2011-09-08, bug=844550: The GeneralizedPublication
# import violates import policy and elicits a warning from the test
# suite.  The warning helps remind us to retire this code as soon as
# possible.
from lp.archivepublisher.domination import (
    Dominator,
    GeneralizedPublication,
    )
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
        entries = packages_map.src_map.get(package_name)

        if entries is None:
            # XXX JeroenVermeulen 2011-09-08, bug=844550: This is a
            # transitional hack.  The database is full of "Published"
            # Debian SPPHs whose packages have actually been deleted.
            # In the future such publications should simply be marked
            # Deleted, but for the legacy baggage we currently carry
            # around we'll just do traditional domination first: pick
            # the latest Published version, and mark the rest of the
            # SPPHs as superseded by that version.  The latest version
            # will then, finally, be marked appropriately Deleted once
            # we remove this transitional hack.
            # To remove the transitional hack, just let live_versions
            # default to the empty list instead of doing this:
            pubs = dominator.findPublishedSPPHs(series, pocket, package_name)
            generalization = GeneralizedPublication(is_source=True)
            pubs_dict = dominator._sortPackages(pubs, generalization)
            sorted_pubs = pubs_dict[package_name]
            if len(sorted_pubs) <= 1:
                # If there's only one published SPPH, the transitional
                # code will just leave it Published.  Don't bother; the
                # migration will be costly enough as it is.
                continue
            live_versions = [sorted_pubs[0].sourcepackagerelease.version]
        else:
            live_versions = [
                entry['Version']
                for entry in entries if 'Version' in entry]

        dominator.dominateRemovedSourceVersions(
            series, pocket, package_name, live_versions)

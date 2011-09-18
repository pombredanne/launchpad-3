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
            import apt_pkg
            from lp.services.database.bulk import load_related
            from lp.soyuz.model.sourcepackagerelease import (
                SourcePackageRelease,
                )
            pubs = list(
                dominator.findPublishedSPPHs(series, pocket, package_name))
            if len(pubs) <= 1:
                # Without at least two published SPPHs, the transitional
                # code will make no changes.  Skip, and leave the
                # algorithm free to assume there's a pubs[0].
                continue
            load_related(
                SourcePackageRelease, pubs, ['sourcepackagereleaseID'])

            # Close off the transaction to avoid being idle-killed.
            # Nothing else is going to supersede or delete these
            # publications in the meantime, so our data stays valid; and
            # if new ones become published, they still won't be
            # considered anyway.
            txn.commit()

            # Find the "latest" publication.  A purely in-memory
            # operation; won't open a new transaction.
            def is_newer(candidate, reference):
                comparison = apt_pkg.VersionCompare(
                    candidate.sourcepackagerelease.version,
                    reference.sourcepackagerelease.version)
                if comparison > 0:
                    return True
                elif comparison < 0:
                    return False
                else:
                    return candidate.datecreated > reference.datecreated

            latest_pub = pubs[0]
            for pub in pubs[1:]:
                if is_newer(pub, latest_pub):
                    latest_pub = pub
            live_versions = [latest_pub.sourcepackagerelease.version]
        else:
            live_versions = [
                entry['Version']
                for entry in entries if 'Version' in entry]

        dominator.dominateRemovedSourceVersions(
            series, pocket, package_name, live_versions)

        txn.commit()

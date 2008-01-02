# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Archive Domination class.

We call 'domination' the procedure used to identify and supersede all
old versions for a given publication, source or binary, inside a suite
(distroseries + pocket, for instance, gutsy or gutsy-updates).

It also processes the superseded publications and makes the ones with
unnecessary files 'eligible for removal', which will then be considered
for archive removal.  See deathrow.py.

In order to judge if a source is 'eligible for removal' it also checks
if its resulting binaries are not necessary any more in the archive, i.e.,
old binary publications can (and should) hold sources in the archive.

Source version life-cycle example:

  * foo_2.1: currently published, source and binary files live in the archive
             pool and it is listed in the archive indexes.

  * foo_2.0: superseded, it's not listed in archive indexes but one of its
             files is used for foo_2.1 (the orig.tar.gz) or foo_2.1 could
             not build for one or more architectures that foo_2.0 could;

  * foo_1.8: eligible for removal, none of its files are required in the
             archive since foo_2.0 was published (new orig.tar.gz) and none
             of its binaries are published (foo_2.0 was completely built)

  * foo_1.0: removed, it already passed through the quarantine period and its
             files got removed from the archive.

Note that:

  * PUBLISHED and SUPERSEDED are publishing statuses.

  * 'eligible for removal' is a combination of SUPERSEDED or DELETED
    publishing status and a defined (non-empty) 'scheduleddeletiondate'.

  * 'removed' is a combination of 'eligible for removal' and a defined
    (non-empy) 'dateremoved'.

The 'domination' procedure is the 2nd step of the publication pipeline and
it is performed for each suite using:

  * judgeAndDominate(distroseries, pocket, pubconfig)

"""

__metaclass__ = type

__all__ = ['Dominator']

import apt_pkg
from datetime import timedelta
import gc

from canonical.archivepublisher import ELIGIBLE_DOMINATION_STATES
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    sqlvalues, flush_database_updates, cursor,
    clear_current_connection_cache)

# Importing from canonical.launchpad.database will cause a circular import
# because we import from this file into database/distributionmirror.py
from canonical.launchpad.database.publishing import (
     BinaryPackagePublishingHistory, SecureSourcePackagePublishingHistory,
     SecureBinaryPackagePublishingHistory)
from canonical.launchpad.interfaces import PackagePublishingStatus


def clear_cache():
    """Flush SQLObject updates and clear the cache."""
    # Flush them anyway, should basically be a noop thanks to not doing
    # lazyUpdate.
    flush_database_updates()
    clear_current_connection_cache()
    gc.collect()

PENDING = PackagePublishingStatus.PENDING
PUBLISHED = PackagePublishingStatus.PUBLISHED
SUPERSEDED = PackagePublishingStatus.SUPERSEDED
DELETED = PackagePublishingStatus.DELETED
OBSOLETE = PackagePublishingStatus.OBSOLETE

# Ugly, but works
apt_pkg.InitSystem()

def _compare_source_packages_by_version_and_date(p1, p2):
    """Compare packages p1 and p2 by their version; using Debian rules.

    If the comparison is the same sourcepackagerelease, compare by datecreated
    instead. So later records beat earlier ones.
    """
    if p1.sourcepackagerelease.id == p2.sourcepackagerelease.id:
        return cmp(p1.datecreated, p2.datecreated)

    return apt_pkg.VersionCompare(p1.sourcepackagerelease.version,
                                  p2.sourcepackagerelease.version)

def _compare_binary_packages_by_version_and_date(p1, p2):
    """Compare packages p1 and p2 by their version; using Debian rules

    If the comparison is the same binarypackagerelease, compare by datecreated
    instead. So later records beat earlier ones.
    """
    if p1.binarypackagerelease.id == p2.binarypackagerelease.id:
        return cmp(p1.datecreated, p2.datecreated)

    return apt_pkg.VersionCompare(p1.binarypackagerelease.version,
                                  p2.binarypackagerelease.version)

class Dominator:
    """ Manage the process of marking packages as superseded.

    Packages are marked as superseded when they become obsolete.
    """

    def __init__(self, logger, archive):
        """Initialise the dominator.

        This process should be run after the publisher has published
        new stuff into the distribution but before the publisher
        creates the file lists for apt-ftparchive.
        """
        self._logger = logger
        self.archive = archive
        self.debug = self._logger.debug

    def _dominateSource(self, sourceinput):
        """
        Perform dominations for source.
        """
        self.debug("Dominating sources...")
        for sourcename in sourceinput.keys():
            # source is a list of versions ordered most-recent-first
            # basically skip the first entry because that is
            # never dominated by us, then just set subsequent entries
            # to SUPERSEDED unless they're already there or pending
            # removal
            assert sourceinput[sourcename], (
                "Empty list of publications for %s" % sourcename)
            super_release = sourceinput[sourcename][0].sourcepackagerelease
            super_release_name = super_release.sourcepackagename.name
            for pubrec in sourceinput[sourcename][1:]:
                if pubrec.status == PUBLISHED or pubrec.status == PENDING:
                    this_release = pubrec.sourcepackagerelease

                    this_release_name = this_release.sourcepackagename.name
                    self.debug(
                        "%s/%s has been judged as superseded by %s/%s" %
                        (this_release_name, this_release.version,
                         super_release_name, super_release.version))

                    pubrec.status = SUPERSEDED
                    pubrec.datesuperseded = UTC_NOW
                    pubrec.supersededby = super_release

    def _getOtherBinaryPublications(self, dominated):
        """Return remaining publications of the same binarypackagerelease."""
        dominated_series = dominated.distroarchseries.distroseries
        available_architectures = [
            das.id for das in dominated_series.architectures]
        query = """
            SecureBinaryPackagePublishingHistory.status IN %s AND
            SecureBinaryPackagePublishingHistory.distroarchseries IN %s AND
            SecureBinaryPackagePublishingHistory.binarypackagerelease = %s AND
            SecureBinaryPackagePublishingHistory.pocket = %s
        """ % sqlvalues([PUBLISHED, PENDING], available_architectures,
                        dominated.binarypackagerelease, dominated.pocket)
        return SecureBinaryPackagePublishingHistory.select(query)

    def _dominateBinary(self, dominated, dominant):
        """Dominate the given binarypackagerelease publication."""
        # At this point only PUBLISHED (ancient versions) or PENDING (
        # multiple overrides/copies) publications should be given. We
        # tolerate SUPERSEDED architecture-independent binaries, because
        # they are dominated automatically once the first publication is
        # processed.
        if dominated.status not in [PUBLISHED, PENDING]:
            arch_independent = (
                dominated.binarypackagerelease.architecturespecific == False)
            assert arch_independent, (
                "Should not dominate unpublished architecture specific "
                "binary %s (%s)" % (
                dominated.binarypackagerelease.title,
                dominated.distroarchseries.architecturetag))
            return

        dominant_build = dominant.binarypackagerelease.build
        distroarchseries = dominant_build.distroarchseries
        self.debug(
            "The %s build of %s has been judged as superseded by the build "
            "of %s.  Arch-specific == %s" % (
            distroarchseries.architecturetag,
            dominated.binarypackagerelease.title,
            dominant.binarypackagerelease.build.sourcepackagerelease.title,
            dominated.binarypackagerelease.architecturespecific))
        dominated.status = SUPERSEDED
        dominated.datesuperseded = UTC_NOW
        # Binary package releases are superseded by the new build,
        # not the new binary package release. This is because
        # there may not *be* a new matching binary package -
        # source packages can change the binaries they build
        # between releases.
        dominated.supersededby = dominant_build

    def _dominateBinaries(self, binaryinput):
        """Perform dominations for binaries."""
        self.debug("Dominating binaries...")
        for binaryname in binaryinput.keys():
            # binary is a list of versions ordered most-recent-first
            # basically skip the first entry because that is
            # never dominated by us, then just set subsequent entries
            # to SUPERSEDED unless they're already there or pending
            # removal
            assert binaryinput[binaryname], (
                "Empty list of publications for %s" % binaryname)
            # At some future point, this code might automatically locate
            # binaries which are no longer built from source (NBS).
            # Currently this is done in archive cruft check.
            dominant = binaryinput[binaryname][0]
            for dominated in binaryinput[binaryname][1:]:
                # Dominate all publications of architecture independent
                # binaries altogether in this distroseries and pocket.
                if not dominated.binarypackagerelease.architecturespecific:
                    other_publications = self._getOtherBinaryPublications(
                        dominated)
                    for dominated in other_publications:
                        self._dominateBinary(dominated, dominant)
                else:
                    self._dominateBinary(dominated, dominant)


    def _sortPackages(self, pkglist, isSource=True):
        # pkglist is a list of packages with the following
        #  * sourcepackagename or packagename as appropriate
        #  * version
        #  * status
        # Don't care about any other attributes
        outpkgs = {}

        if isSource:
            self.debug("Sorting sources...")
        else:
            self.debug("Sorting binaries...")

        for inpkg in pkglist:
            if isSource:
                L = outpkgs.setdefault(
                    inpkg.sourcepackagerelease.sourcepackagename.name.encode(
                    'utf-8'), [])
            else:
                L = outpkgs.setdefault(
                    inpkg.binarypackagerelease.binarypackagename.name.encode(
                    'utf-8'), [])

            L.append(inpkg)

        for pkgname in outpkgs:
            if len(outpkgs[pkgname]) > 1:
                if isSource:
                    outpkgs[pkgname].sort(
                        _compare_source_packages_by_version_and_date)
                else:
                    outpkgs[pkgname].sort(
                        _compare_binary_packages_by_version_and_date)

                outpkgs[pkgname].reverse()

        return outpkgs

    def _setScheduledDeletionDate(self, pub_record, conf):
        """Set the scheduleddeletiondate on a publishing record.

        If the status is DELETED we set the date to UTC_NOW, otherwise
        it gets the configured stay of execution period.
        """
        if pub_record.status == PackagePublishingStatus.DELETED:
            pub_record.scheduleddeletiondate = UTC_NOW
        else:
            pub_record.scheduleddeletiondate = (
                UTC_NOW + timedelta(days=conf.stayofexecution))

    def _judgeSuperseded(self, source_records, binary_records, conf):
        """Determine whether the superseded packages supplied should
        be moved to death row or not.

        Currently this is done by assuming that any superseded binary
        package should be removed. In the future this should attempt
        to supersede binaries in build-sized chunks only, bug 55030.

        Superseded source packages are considered removable when they
        have no binaries in this distroseries which are published or
        superseded

        When a package is considered for death row it is given a
        'scheduled deletion date' of now plus the defined 'stay of execution'
        time provided in the configuration parameter.
        """

        self.debug("Beginning superseded processing...")

        # XXX: dsilvers 2005-09-22 bug=55030:
        # Need to make binaries go in groups but for now this'll do.
        # An example of the concrete problem here is:
        # - Upload foo-1.0, which builds foo and foo-common (arch all).
        # - Upload foo-1.1, ditto.
        # - foo-common-1.1 is built (along with the i386 binary for foo)
        # - foo-common-1.0 is superseded
        # Foo is now uninstallable on any architectures which don't yet
        # have a build of foo-1.1, as the foo-common for foo-1.0 is gone.

        # Essentially we ideally don't want to lose superseded binaries
        # unless the entire group is ready to be made pending removal.
        # In this instance a group is defined as all the binaries from a
        # given build. This assumes we've copied the arch_all binaries
        # from whichever build provided them into each arch-specific build
        # which we publish. If instead we simply publish the arch-all
        # binaries from another build then instead we should scan up from
        # the binary to its source, and then back from the source to each
        # binary published in *this* distroarchseries for that source.
        # if the binaries as a group (in that definition) are all superseded
        # then we can consider them eligible for removal.
        for pub_record in binary_records:
            binpkg_release = pub_record.binarypackagerelease
            self.debug("%s/%s (%s) has been judged eligible for removal" %
                       (binpkg_release.binarypackagename.name,
                        binpkg_release.version,
                        pub_record.distroarchseries.architecturetag))
            self._setScheduledDeletionDate(pub_record, conf)
            # XXX cprov 20070820: 'datemadepending' is useless, since it's
            # always equals to "scheduleddeletiondate - quarantine".
            pub_record.datemadepending = UTC_NOW

        for pub_record in source_records:
            srcpkg_release = pub_record.sourcepackagerelease
            # Attempt to find all binaries of this
            # SourcePackageRelease which are/have been in this
            # distroseries...
            considered_binaries = BinaryPackagePublishingHistory.select("""
            binarypackagepublishinghistory.distroarchseries =
                distroarchseries.id AND
            binarypackagepublishinghistory.scheduleddeletiondate IS NULL AND
            binarypackagepublishinghistory.archive = %s AND
            build.sourcepackagerelease = %s AND
            distroarchseries.distroseries = %s AND
            binarypackagepublishinghistory.binarypackagerelease =
            binarypackagerelease.id AND
            binarypackagerelease.build = build.id AND
            binarypackagepublishinghistory.pocket = %s
            """ % sqlvalues(self.archive, srcpkg_release,
                            pub_record.distroseries, pub_record.pocket),
            clauseTables=['DistroArchSeries', 'BinaryPackageRelease','Build'])

            # There is at least one non-removed binary to consider
            if considered_binaries.count() > 0:
                # However we can still remove *this* record if there's
                # at least one other PUBLISHED for the spr. This happens
                # when a package is moved between components.
                published = SecureSourcePackagePublishingHistory.selectBy(
                    distroseries=pub_record.distroseries,
                    pocket=pub_record.pocket,
                    status=PackagePublishingStatus.PUBLISHED,
                    archive=self.archive,
                    sourcepackagereleaseID=srcpkg_release.id)
                # Zero PUBLISHED for this spr, so nothing to take over
                # for us, so leave it for consideration next time.
                if published.count() == 0:
                    continue

            # Okay, so there's no unremoved binaries, let's go for it...
            self.debug(
                "%s/%s (%s) source has been judged eligible for removal" %
                (srcpkg_release.sourcepackagename.name,
                 srcpkg_release.version, pub_record.id))
            self._setScheduledDeletionDate(pub_record, conf)
            # XXX cprov 20070820: 'datemadepending' is pointless, since it's
            # always equals to "scheduleddeletiondate - quarantine".
            pub_record.datemadepending = UTC_NOW

    def judgeAndDominate(self, dr, pocket, config, do_clear_cache=True):
        """Perform the domination and superseding calculations

        It only works across the distroseries and pocket specified.
        """
        for distroarchseries in dr.architectures:
            self.debug("Performing domination across %s/%s (%s)" % (
                dr.name, pocket.title, distroarchseries.architecturetag))

            # Here we go behind SQLObject's back to generate an assistance
            # table which will seriously improve the performance of this
            # part of the publisher.
            # XXX: dsilvers 2006-02-04: It would be nice to not have to do
            # this. Most of this methodology is stolen from person.py
            # XXX: malcc 2006-08-03: This should go away when we shift to
            # doing this one package at a time.
            flush_database_updates()
            cur = cursor()
            cur.execute("""SELECT bpn.id AS name, count(bpn.id) AS count INTO
                temporary table PubDomHelper FROM BinaryPackageRelease bpr,
                BinaryPackageName bpn, SecureBinaryPackagePublishingHistory
                sbpph WHERE bpr.binarypackagename = bpn.id AND
                sbpph.binarypackagerelease = bpr.id AND
                sbpph.distroarchseries = %s AND sbpph.archive = %s AND
                sbpph.status = %s AND sbpph.pocket = %s
                GROUP BY bpn.id""" % sqlvalues(
                distroarchseries, self.archive,
                PackagePublishingStatus.PUBLISHED, pocket))

            binaries = SecureBinaryPackagePublishingHistory.select(
                """
                securebinarypackagepublishinghistory.distroarchseries = %s
                AND securebinarypackagepublishinghistory.archive = %s
                AND securebinarypackagepublishinghistory.pocket = %s
                AND securebinarypackagepublishinghistory.status = %s AND
                securebinarypackagepublishinghistory.binarypackagerelease =
                    binarypackagerelease.id
                AND binarypackagerelease.binarypackagename IN (
                    SELECT name FROM PubDomHelper WHERE count > 1)"""
                % sqlvalues (distroarchseries, self.archive,
                             pocket, PackagePublishingStatus.PUBLISHED),
                clauseTables=['BinaryPackageRelease'])

            self._dominateBinaries(self._sortPackages(binaries, False))
            if do_clear_cache:
                self.debug("Flushing SQLObject cache.")
                clear_cache()

            flush_database_updates()
            cur.execute("DROP TABLE PubDomHelper")

        if do_clear_cache:
            self.debug("Flushing SQLObject cache.")
            clear_cache()

        self.debug("Performing domination across %s/%s (Source)" %
                   (dr.name, pocket.title))
        # We can use SecureSourcePackagePublishingHistory here because
        # the standard .selectBy automatically says that embargo
        # should be false.
        sources = SecureSourcePackagePublishingHistory.selectBy(
            distroseries=dr, archive=self.archive, pocket=pocket,
            status=PackagePublishingStatus.PUBLISHED)
        self._dominateSource(self._sortPackages(sources))
        flush_database_updates()

        sources = SecureSourcePackagePublishingHistory.select("""
            securesourcepackagepublishinghistory.distroseries = %s AND
            securesourcepackagepublishinghistory.archive = %s AND
            securesourcepackagepublishinghistory.pocket = %s AND
            securesourcepackagepublishinghistory.status IN %s AND
            securesourcepackagepublishinghistory.scheduleddeletiondate is NULL
            """ % sqlvalues(dr, self.archive, pocket,
                            ELIGIBLE_DOMINATION_STATES))

        binaries = SecureBinaryPackagePublishingHistory.select("""
            securebinarypackagepublishinghistory.distroarchseries =
                distroarchseries.id AND
            distroarchseries.distroseries = %s AND
            securebinarypackagepublishinghistory.archive = %s AND
            securebinarypackagepublishinghistory.pocket = %s AND
            securebinarypackagepublishinghistory.status IN %s AND
            securebinarypackagepublishinghistory.scheduleddeletiondate is NULL
            """ % sqlvalues(dr, self.archive, pocket,
                            ELIGIBLE_DOMINATION_STATES),
            clauseTables=['DistroArchSeries'])

        self._judgeSuperseded(sources, binaries, config)

        self.debug("Domination for %s/%s finished" %
                   (dr.name, pocket.title))


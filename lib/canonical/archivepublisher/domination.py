# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# This is the python package that defines the
# 'canonical.archivepublisher.domination' package. This package is
# related to the domination of old source and binary releases inside
# the publishing tables.

__metaclass__ = type


import apt_pkg
from datetime import timedelta
import gc

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    sqlvalues, flush_database_updates, cursor,
    clear_current_connection_cache)

# Importing from canonical.launchpad.database will cause a circular import
# because we import from this file into database/distributionmirror.py
from canonical.launchpad.database.publishing import (
     BinaryPackagePublishingHistory, SecureSourcePackagePublishingHistory,
     SecureBinaryPackagePublishingHistory)
from canonical.lp.dbschema import PackagePublishingStatus


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

        for source in sourceinput:
            # source is a list of versions ordered most-recent-first
            # basically skip the first entry because that is
            # never dominated by us, then just set subsequent entries
            # to SUPERSEDED unless they're already there or pending
            # removal
            assert sourceinput[source] is not None
            super_release = sourceinput[source][0].sourcepackagerelease
            super_release_name = super_release.sourcepackagename.name
            for pubrec in sourceinput[source][1:]:
                if pubrec.status == PUBLISHED or pubrec.status == PENDING:
                    this_release = pubrec.sourcepackagerelease

                    this_release_name = this_release.sourcepackagename.name
                    self.debug("%s/%s has been judged as superseded by %s/%s" %
                               (this_release_name, this_release.version,
                                super_release_name, super_release.version))

                    pubrec.status = SUPERSEDED;
                    pubrec.datesuperseded = UTC_NOW;
                    pubrec.supersededby = super_release

    def _dominateBinary(self, binaryinput):
        """
        Perform dominations for binaries.
        """

        self.debug("Dominating binaries...")

        for binary in binaryinput:
            # binary is a list of versions ordered most-recent-first
            # basically skip the first entry because that is
            # never dominated by us, then just set subsequent entries
            # to SUPERSEDED unless they're already there or pending
            # removal

            # At some future point, this code might automatically locate
            # binaries which are no longer built from source (NBS).
            # Currently this is done in archive cruft check.
            dominantrelease = binaryinput[binary][0].binarypackagerelease
            for pubrec in binaryinput[binary][1:]:
                if pubrec.status == PUBLISHED or pubrec.status == PENDING:
                    thisrelease = pubrec.binarypackagerelease
                    self.debug("The %s build of %s/%s has been judged "
                               "as superseded by the %s build of %s/%s.  "
                               "Arch-specific == %s" % (
                        thisrelease.build.distroarchseries.architecturetag,
                        thisrelease.binarypackagename.name,
                        thisrelease.version,
                        dominantrelease.build.distroarchseries.architecturetag,
                        dominantrelease.binarypackagename.name,
                        dominantrelease.version,
                        thisrelease.architecturespecific))
                    pubrec.status = SUPERSEDED;
                    pubrec.datesuperseded = UTC_NOW;
                    # Binary package releases are superseded by the new build,
                    # not the new binary package release. This is because there
                    # may not *be* a new matching binary package - source
                    # packages can change the binaries they build between
                    # releases.
                    pubrec.supersededby = dominantrelease.build


    def _sortPackages(self, pkglist, isSource = True):
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
            pub_record.scheduleddeletiondate = (
                UTC_NOW + timedelta(days=conf.stayofexecution))
            # XXX cprov 20070820: it is useless, since it's always equals
            # to scheduleddeletiondate - quarantine.
            pub_record.datemadepending = UTC_NOW

        for pub_record in source_records:
            srcpkg_release = pub_record.sourcepackagerelease
            # Attempt to find all binaries of this
            # SourcePackageRelease which are/have been in this
            # distroseries...
            considered_binaries = BinaryPackagePublishingHistory.select("""
            binarypackagepublishinghistory.distroarchrelease =
                distroarchrelease.id AND
            binarypackagepublishinghistory.scheduleddeletiondate IS NULL AND
            binarypackagepublishinghistory.archive = %s AND
            build.sourcepackagerelease = %s AND
            distroarchrelease.distrorelease = %s AND
            binarypackagepublishinghistory.binarypackagerelease =
            binarypackagerelease.id AND
            binarypackagerelease.build = build.id AND
            binarypackagepublishinghistory.pocket = %s
            """ % sqlvalues(self.archive, srcpkg_release,
                            pub_record.distroseries, pub_record.pocket),
            clauseTables=['DistroArchRelease', 'BinaryPackageRelease','Build'])

            # There is at least one non-removed binary to consider
            if considered_binaries.count() > 0:
                # XXX malcc 2006-10-17 bug=57488:
                # Want to change to running scripts at info level,
                # but for now just shut up this particularly noisy
                # debug statement.
                #self.debug("%s/%s (source) has at least %d non-removed "
                #           "binaries as yet" % (
                #    srcpkg_release.sourcepackagename.name,
                #    srcpkg_release.version,
                #    considered_binaries.count()))

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
            pub_record.scheduleddeletiondate = (
                UTC_NOW + timedelta(days=conf.stayofexecution))
            # XXX cprov 20070820: it is useless, since it's always equals
            # to scheduleddeletiondate - quarantine.
            pub_record.datemadepending = UTC_NOW

    def judgeAndDominate(self, dr, pocket, config, do_clear_cache=True):
        """Perform the domination and superseding calculations

        It only works across the distroseries and pocket specified.
        """
        self.debug("Performing domination across %s/%s (Source)" %
                   (dr.name, pocket.title))

        # We can use SecureSourcePackagePublishingHistory here because
        # the standard .selectBy automatically says that embargo
        # should be false.

        sources = SecureSourcePackagePublishingHistory.selectBy(
            distroseries=dr, archive=self.archive, pocket=pocket,
            status=PackagePublishingStatus.PUBLISHED)

        self._dominateSource(self._sortPackages(sources))

        if do_clear_cache:
            self.debug("Flushing SQLObject cache.")
            clear_cache()

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
                sbpph.distroarchrelease = %s AND sbpph.archive = %s AND
                sbpph.status = %s AND sbpph.pocket = %s
                GROUP BY bpn.id""" % sqlvalues(
                distroarchseries, self.archive,
                PackagePublishingStatus.PUBLISHED, pocket))

            binaries = SecureBinaryPackagePublishingHistory.select(
                """
                securebinarypackagepublishinghistory.distroarchrelease = %s
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

            self._dominateBinary(self._sortPackages(binaries, False))
            if do_clear_cache:
                self.debug("Flushing SQLObject cache.")
                clear_cache()

            flush_database_updates()
            cur.execute("DROP TABLE PubDomHelper")

        dominate_status = [
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.DELETED,
            ]

        sources = SecureSourcePackagePublishingHistory.select("""
            securesourcepackagepublishinghistory.distrorelease = %s AND
            securesourcepackagepublishinghistory.archive = %s AND
            securesourcepackagepublishinghistory.pocket = %s AND
            securesourcepackagepublishinghistory.status IN %s AND
            securesourcepackagepublishinghistory.scheduleddeletiondate is NULL
            """ % sqlvalues(dr, self.archive, pocket, dominate_status))

        binaries = SecureBinaryPackagePublishingHistory.select("""
            securebinarypackagepublishinghistory.distroarchrelease =
                distroarchrelease.id AND
            distroarchrelease.distrorelease = %s AND
            securebinarypackagepublishinghistory.archive = %s AND
            securebinarypackagepublishinghistory.pocket = %s AND
            securebinarypackagepublishinghistory.status IN %s AND
            securebinarypackagepublishinghistory.scheduleddeletiondate is NULL
            """ % sqlvalues(dr, self.archive, pocket, dominate_status),
            clauseTables=['DistroArchRelease'])

        self._judgeSuperseded(sources, binaries, config)

        self.debug("Domination for %s/%s finished" %
                   (dr.name, pocket.title))


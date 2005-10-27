# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# This is the python package that defines the
# 'canonical.archivepublisher.domination' package. This package is
# related to the domination of old source and binary releases inside
# the publishing tables.

from sourcerer.deb.version import (
    Version as DebianVersion, BadUpstreamError)

from canonical.lp.dbschema import PackagePublishingStatus

from canonical.database.constants import UTC_NOW

from canonical.launchpad.database import (
     BinaryPackagePublishing, SecureSourcePackagePublishingHistory,
     SecureBinaryPackagePublishingHistory)

from canonical.database.sqlbase import sqlvalues

PENDING = PackagePublishingStatus.PENDING
PUBLISHED = PackagePublishingStatus.PUBLISHED
SUPERSEDED = PackagePublishingStatus.SUPERSEDED
PENDINGREMOVAL = PackagePublishingStatus.PENDINGREMOVAL

# For stayofexecution processing in judgeSuperseded
from datetime import timedelta

def _compare_source_packages_by_version(p1, p2):
    """Compare packages p1 and p2 by their version; using Debian rules.
    
    If we're unable to parse the version number as a debian version (E.g.
    if it does not comply with policy but we had to import it anyway,
    then we compare it directly as strings.
    """
    try:
        v1 = DebianVersion(p1.sourcepackagerelease.version)
        v2 = DebianVersion(p2.sourcepackagerelease.version)
        return cmp(v1, v2)
    except BadUpstreamError:
        return cmp(p1, p2)
    
def _compare_binary_packages_by_version(p1, p2):
    """Compare packages p1 and p2 by their version; using Debian rules
    
    If we're unable to parse the version number as a debian version (E.g.
    if it does not comply with policy but we had to import it anyway,
    then we compare it directly as strings.
    """
    try:
        v1 = DebianVersion(p1.binarypackagerelease.version)
        v2 = DebianVersion(p2.binarypackagerelease.version)
        return cmp(v1, v2)
    except BadUpstreamError:
        return cmp(p1, p2)


class Dominator(object):
    """
    Manage the process of marking packages as superseded in the publishing
    tables as and when they become obsolete.
    """

    def __init__(self, logger):
        """
        Initialise the dominator. This process should be run after the
        publisher has published new stuff into the distribution but before
        the publisher creates the file lists for apt-ftparchive
        """
        object.__init__(self)
        self._logger = logger
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

            # XXX: what happens when sourceinput[source] is None, or can
            # we assert it's not None?
            #   -- kiko, 2005-09-23
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
            # XXX dsilvers 2004-11-11 This needs work. Unfortunately I'm not
            # Completely sure how to correct for this.
            # For now; treat domination of binaries the same as for source
            # I.E. dominate by name only and highest version wins.

            # binary is a list of versions ordered most-recent-first
            # basically skip the first entry because that is
            # never dominated by us, then just set subsequent entries
            # to SUPERSEDED unless they're already there or pending
            # removal
            dominantrelease = binaryinput[binary][0].binarypackagerelease
            for pubrec in binaryinput[binary][1:]:
                if pubrec.status == PUBLISHED or pubrec.status == PENDING:
                    thisrelease = pubrec.binarypackagerelease
                    self.debug("The %s build of %s/%s has been judged "
                               "as superseded by the %s build of %s/%s.  "
                               "Arch-specific == %s" % (
                        thisrelease.build.distroarchrelease.architecturetag,
                        thisrelease.binarypackagename.name,
                        thisrelease.version,
                        dominantrelease.build.distroarchrelease.architecturetag,
                        dominantrelease.binarypackagename.name,
                        dominantrelease.version,
                        thisrelease.architecturespecific))
                    pubrec.status = SUPERSEDED;
                    pubrec.datesuperseded = UTC_NOW;
                    # XXX is this really .build? When superseding above
                    # we set supersededby = super_release..
                    #   -- kiko, 2005-09-23
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
                    outpkgs[pkgname].sort(_compare_source_packages_by_version)
                else:
                    outpkgs[pkgname].sort(_compare_binary_packages_by_version)
                    
                outpkgs[pkgname].reverse()

        return outpkgs

    def _judgeSuperseded(self, source_records, binary_records, conf):
        """Determine whether the superseded packages supplied should
        be moved to death row or not.

        Currently this is done by assuming that any superseded binary
        package should be removed. In the future this should attempt
        to supersede binaries in build-sized chunks only.

        Superseded source packages are considered removable when they
        have no binaries in this distrorelease which are published or
        superseded

        When a package is considered for death row its status in the
        publishing table is set to PENDINGREMOVAL and the
        datemadepending is set to now.

        The package is then given a scheduled deletion date of now
        plus the defined stay of execution time provided in the
        configuration parameter.
        """

        self.debug("Beginning superseded processing...")

        # XXX: dsilvers: 20050922: Need to make binaries go in groups
        # but for now this'll do.
        # Essentially we ideally don't want to lose superseded binaries
        # unless the entire group is ready to be made pending removal.
        # In this instance a group is defined as all the binaries from a
        # given build. This assumes we've copied the arch_all binaries
        # from whichever build provided them into each arch-specific build
        # which we publish. If instead we simply publish the arch-all
        # binaries from another build then instead we should scan up from
        # the binary to its source, and then back from the source to each
        # binary published in *this* distroarchrelease for that source.
        # if the binaries as a group (in that definition) are all superseded
        # then we can consider them eligible for removal.
        for pub_record in binary_records:
            binpkg_release = pub_record.binarypackagerelease
            if pub_record.status == SUPERSEDED:
                self.debug("%s/%s (%s) has been judged eligible for removal" %
                           (binpkg_release.binarypackagename.name,
                            binpkg_release.version,
                            pub_record.distroarchrelease.architecturetag))
                pub_record.status = PENDINGREMOVAL
                pub_record.scheduleddeletiondate = UTC_NOW + \
                                          timedelta(days=conf.stayofexecution)
                pub_record.datemadepending = UTC_NOW

        for pub_record in source_records:
            srcpkg_release = pub_record.sourcepackagerelease
            if pub_record.status == SUPERSEDED:
                # Attempt to find all binaries of this
                # SourcePackageReleace which are/have been in this
                # distrorelease...
                considered_binaries = BinaryPackagePublishing.select('''
                    (binarypackagepublishing.status = %s OR
                     binarypackagepublishing.status = %s OR
                     binarypackagepublishing.status = %s) AND
                    binarypackagepublishing.distroarchrelease =
                        distroarchrelease.id AND
                    distroarchrelease.distrorelease = %s AND
                    binarypackagepublishing.binarypackagerelease =
                        binarypackagerelease.id AND
                    binarypackagerelease.build = build.id AND
                    build.sourcepackagerelease = %s''' % sqlvalues(
                    PENDING, PUBLISHED, SUPERSEDED,
                    pub_record.distrorelease.id, srcpkg_release.id),
                    clauseTables=['DistroArchRelease', 'BinaryPackageRelease',
                                  'Build'])
                if considered_binaries.count() > 0:
                    # There is at least one non-superseded binary to consider
                    self.debug("%s/%s (source) has at least %d non-removed "
                               "binaries as yet" % (
                        srcpkg_release.sourcepackagename.name,
                        srcpkg_release.version,
                        considered_binaries.count()))
                    continue

                # Okay, so there's no unremoved binaries, let's go for it...
                self.debug(
                    "%s/%s (source) has been judged eligible for removal" %
                           (srcpkg_release.sourcepackagename.name,
                            srcpkg_release.version))
                           
                pub_record.status = PENDINGREMOVAL
                pub_record.scheduleddeletiondate = UTC_NOW + \
                                          timedelta(days=conf.stayofexecution)
                pub_record.datemadepending = UTC_NOW


    def judgeAndDominate(self, dr, pocket, config):
        """Perform the domination and superseding calculations across the
        distrorelease and pocket specified."""
        

        self.debug("Performing domination across %s/%s (Source)" %
                   (dr.name, pocket.title))

        # We can use SecureSourcePackagePublishingHistory here because
        # the standard .selectBy automatically says that embargo
        # should be false.

        sources = SecureSourcePackagePublishingHistory.selectBy(
            distroreleaseID=dr.id, pocket=pocket,
            status=PackagePublishingStatus.PUBLISHED)

        self._dominateSource(self._sortPackages(sources))

        for distroarchrelease in dr.architectures:
            self.debug("Performing domination across %s/%s (%s)" % (
                dr.name, pocket.title, distroarchrelease.architecturetag))
            
            binaries = SecureBinaryPackagePublishingHistory.selectBy(
                distroarchreleaseID=distroarchrelease.id,
                pocket=pocket,
                status=PackagePublishingStatus.PUBLISHED)
            
            self._dominateBinary(self._sortPackages(binaries, False))
        
        sources = SecureSourcePackagePublishingHistory.selectBy(
            distroreleaseID=dr.id, pocket=pocket,
            status=PackagePublishingStatus.SUPERSEDED)
        
        binaries = SecureBinaryPackagePublishingHistory.select("""
            securebinarypackagepublishinghistory.distroarchrelease =
                distroarchrelease.id AND
            distroarchrelease.distrorelease = %s AND
            securebinarypackagepublishinghistory.status = %s""" % sqlvalues(
            dr.id, PackagePublishingStatus.SUPERSEDED), clauseTables=[
            'DistroArchRelease'])

        self._judgeSuperseded(sources, binaries, config)

        self.debug("Domination for %s/%s finished" %
                   (dr.name, pocket.title))

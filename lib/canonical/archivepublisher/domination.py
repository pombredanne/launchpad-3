# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# This is the python package that defines the
# 'canonical.archivepublisher.domination' package. This package is
# related to the domination of old source and binary releases inside
# the publishing tables.

from canonical.sourcerer.deb.version import Version as DebianVersion

from canonical.lp.dbschema import PackagePublishingStatus

from canonical.database.constants import UTC_NOW

from canonical.launchpad.database import (
     SourcePackagePublishing, BinaryPackagePublishing,
     SecureSourcePackagePublishingHistory,
     SecureBinaryPackagePublishingHistory)

from canonical.database.sqlbase import sqlvalues

PENDING = PackagePublishingStatus.PENDING
PUBLISHED = PackagePublishingStatus.PUBLISHED
SUPERSEDED = PackagePublishingStatus.SUPERSEDED
PENDINGREMOVAL = PackagePublishingStatus.PENDINGREMOVAL

# For stayofexecution processing in judgeSuperseded
from datetime import timedelta

def _compare_source_packages_by_version(p1, p2):
    """Compare packages p1 and p2 by their version; using Debian rules"""
    v1 = DebianVersion(p1.sourcepackagerelease.version)
    v2 = DebianVersion(p2.sourcepackagerelease.version)
    return cmp(v1, v2)
    
def _compare_binary_packages_by_version(p1, p2):
    """Compare packages p1 and p2 by their version; using Debian rules"""
    v1 = DebianVersion(p1.binarypackagerelease.version)
    v2 = DebianVersion(p2.binarypackagerelease.version)
    return cmp(v1, v2)
    

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

            for pubrec in sourceinput[source][1:]:
                if pubrec.status == PUBLISHED or pubrec.status == PENDING:
                    self.debug("%s/%s has been judged as superseded by %s/%s" %
                               (pubrec.sourcepackagerelease.sourcepackagename.name,
                                pubrec.sourcepackagerelease.version,
                                sourceinput[source][0].sourcepackagerelease.sourcepackagename.name,
                                sourceinput[source][0].sourcepackagerelease.version))
                    pubrec.status = SUPERSEDED;
                    pubrec.datesuperseded = UTC_NOW;
                    pubrec.supersededby = sourceinput[source][0].sourcepackagerelease

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
                    self.debug("The %s build of %s/%s has been judged as superseded by the %s build of %s/%s. Arch-specific == %s" % (
                        thisrelease.build.distroarchrelease.architecturetag,
                        thisrelease.binarypackagename.name,
                        thisrelease.version,
                        dominantrelease.build.distroarchrelease.architecturetag,
                        dominantrelease.binarypackagename.name,
                        dominantrelease.version,
                        thisrelease.architecturespecific))
                    pubrec.status = SUPERSEDED;
                    pubrec.datesuperseded = UTC_NOW;
                    pubrec.supersededby = binaryinput[binary][0].binarypackagerelease.build


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

    def _judgeSuperseded(self, sourcepackages, binarypackages, conf):
        """Determine whether the superseded packages supplied should be moved
        to death row or not.

        Currently this is done by assuming that any superseded package should
        be removed. In the future this should attempt to supersede binaries
        in build-sized chunks only.

        When a package is considered for death row its status in the publishing
        table is set to PENDINGREMOVAL and the datemadepending is set to now.

        The package is then given a scheduled deletion date of now plus the
        defined stay of execution time provided in the configuration parameter.
        """

        # XXX dsilvers 2004-11-12 This needs work. Unfortunately I'm not
        # completely sure how to correct for this.
        # For now; binaries were dominated as per sources and we just
        # treat everything as entirely separate. Nothing stays superseded
        # but we keep the separation for later correct implementation

        self.debug("Beginning superseded processing...")

        for p in sourcepackages:
            if p.status == SUPERSEDED:
                self.debug("%s/%s (source) has been judged eligible for removal" %
                           (p.sourcepackagerelease.sourcepackagename.name,
                            p.sourcepackagerelease.version))
                           
                p.status = PENDINGREMOVAL
                p.scheduleddeletiondate = UTC_NOW + \
                                          timedelta(days=conf.stayofexecution)
                p.datemadepending = UTC_NOW
        for p in binarypackages:
            if p.status == SUPERSEDED:
                self.debug("%s/%s (%s) has been judged eligible for removal" %
                           (p.binarypackagerelease.binarypackagename.name,
                            p.binarypackagerelease.version,
                            p.distroarchrelease.architecturetag))
                p.status = PENDINGREMOVAL
                p.scheduleddeletiondate = UTC_NOW + \
                                          timedelta(days=conf.stayofexecution)
                p.datemadepending = UTC_NOW

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
            status=PackagePublishingStatus.SUPERSEDED)

        self._dominateSource(self._sortPackages(sources))

        for distroarchrelease in dr.architectures:
            self.debug("Performing domination across %s/%s (%s)" % (
                dr.name, pocket.title, distroarchrelease.architecturetag))
            
            binaries = SecureBinaryPackagePublishingHistory.selectBy(
                distroarchreleaseID=distroarchrelease.id,
                pocket=pocket,
                status=PackagePublishingStatus.SUPERSEDED)
            
            self._dominateBinary(self._sortPackages(binaries, False))
        
        self._judgeSuperseded(sources, binaries, config)

        self.debug("Domination for %s/%s finished" %
                   (dr.name, pocket.title))

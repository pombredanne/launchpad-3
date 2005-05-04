# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# This is the python package that defines the 'canonical.lucille.domination'
# package. This package is related to the domination of old source and binary
# releases inside the publishing tables.

from canonical.sourcerer.deb.version import Version as DebianVersion

from canonical.lp.dbschema import PackagePublishingStatus

PENDING = PackagePublishingStatus.PENDING
PUBLISHED = PackagePublishingStatus.PUBLISHED
SUPERSEDED = PackagePublishingStatus.SUPERSEDED
PENDINGREMOVAL = PackagePublishingStatus.PENDINGREMOVAL

# For stayofexecution processing in judgeSuperseded
from datetime import datetime, timedelta

def _compare_packages_by_version(p1, p2):
    """Compare packages p1 and p2 by their version; using Debian rules"""
    v1 = DebianVersion(p1.version)
    v2 = DebianVersion(p2.version)
    return cmp(v1, v2)
    

class Dominator(object):
    """
    Manage the process of marking packages as superseded in the publishing
    tables as and when they become obsolete.
    """

    def __init__(self, dr):
        """
        Initialise the dominator. This process should be run after the
        publisher has published new stuff into the distribution but before
        the publisher creates the file lists for apt-ftparchive
        """
        object.__init__(self)
        self._dr = dr

    def _dominateSource(self, sourceinput):
        """
        Perform dominations for source.
        """

        for source in sourceinput:
            # source is a list of versions ordered most-recent-first
            # basically skip the first entry because that is
            # never dominated by us, then just set subsequent entries
            # to SUPERSEDED unless they're already there or pending
            # removal

            # SPPHXXX dsilvers 2005-04-15 This needs updating for SPPH
            # as the publisher is written.

            for pubrec in sourceinput[source][1:]:
                if pubrec.status == PUBLISHED or pubrec.status == PENDING:
                    pubrec.status = SUPERSEDED;

    def _dominateBinary(self, binaryinput):
        """
        Perform dominations for binaries.
        """

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
            for pubrec in binaryinput[binary][1:]:
                if pubrec.status == PUBLISHED or pubrec.status == PENDING:
                    pubrec.status = SUPERSEDED;


    def _sortPackages(self, pkglist, isSource = True):
        # pkglist is a list of packages with the following
        #  * sourcepackagename or packagename as appropriate
        #  * version
        #  * status
        # Don't care about any other attributes
        outpkgs = {}

        for inpkg in pkglist:
            if isSource:
                l = outpkgs.setdefault(inpkg.sourcepackagename.encode('utf-8'),
                                       [])
            else:
                l = outpkgs.setdefault(inpkg.packagename.encode('utf-8'), [])

            l.append(inpkg)

        for k in outpkgs:
            if len(outpkgs[k]) > 1:
                outpkgs[k].sort(_compare_packages_by_version)
                outpkgs[k].reverse()

        return outpkgs

    def dominate(self, sourcepackages, binarypackages):
        """Perform dominations across the source and binarypackages
        listed in the input. Dominated packages get their status set
        to SUPERSEDED if appropriate"""
        self._dominateSource( self._sortPackages(sourcepackages) )
        self._dominateBinary( self._sortPackages(binarypackages, False) )

    def judgeSuperseded(self, sourcepackages, binarypackages):
        """Judge whether or the supplied packages (superseded ones anyway)
        should be moved to death row or not"""

        # XXX dsilvers 2004-11-12 This needs work. Unfortunately I'm not
        # completely sure how to correct for this.
        # For now; binaries were dominated as per sources and we just
        # treat everything as entirely separate. Nothing stays superseded
        # but we keep the separation for later correct implementation

        # SPPHXXX dsilvers 2005-04-15 This needs updating for SPPH
        # as the publisher is written.

        for p in sourcepackages:
            if p.status == SUPERSEDED:
                p.status = PENDINGREMOVAL.value
                p.scheduleddeletiondate = datetime.utcnow() + \
                                          timedelta(days=cnf.stayofexecution)
        for p in binarypackages:
            if p.status == SUPERSEDED:
                p.status = PENDINGREMOVAL.value
                p.scheduleddeletiondate = datetime.utcnow() + \
                                          timedelta(days=cnf.stayofexecution)

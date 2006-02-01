# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Classes to represent source package releases in a distribution release."""

__metaclass__ = type

__all__ = [
    'DistroReleaseSourcePackageRelease',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import IDistroReleaseSourcePackageRelease

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.database.build import Build
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory, SourcePackagePublishingHistory)


class DistroReleaseSourcePackageRelease:
    """This is a "Magic SourcePackageRelease in Distro Release". It is not
    an SQLObject but instead it describes the behaviour of a specific
    release of the package in the distrorelease."""

    implements(IDistroReleaseSourcePackageRelease)

    def __init__(self, distrorelease, sourcepackagerelease):
        self.distrorelease = distrorelease
        self.sourcepackagerelease = sourcepackagerelease

    @property
    def name(self):
        """See IDistroReleaseSourcePackageRelease."""
        return self.sourcepackagerelease.sourcepackagename.name

    @property
    def version(self):
        """See IDistroReleaseSourcePackageRelease."""
        return self.sourcepackagerelease.version

    @property
    def distribution(self):
        """See IDistroReleaseSourcePackageRelease."""
        return self.distrorelease.distribution

    @property
    def displayname(self):
        """See IDistroReleaseSourcePackageRelease."""
        return '%s %s' % (self.name, self.version)

    @property
    def title(self):
        """See IDistroReleaseSourcePackageRelease."""
        return '%s %s (source) in %s %s' % (
            self.name, self.version, self.distribution.name,
            self.distrorelease.name)

    @property
    def current_publishing_record(self):
        """An internal property used by methods of this class to know where
        this release is or was published.
        """
        pub_hist = self.publishing_history
        if pub_hist.count() == 0:
            return None
        return pub_hist[0]

    @property
    def pocket(self):
        """See IDistroReleaseSourcePackageRelease."""
        currpub = self.current_publishing_record
        if currpub is None:
            return None
        return currpub.pocket

    @property
    def section(self):
        """See IDistroReleaseSourcePackageRelease."""
        currpub = self.current_publishing_record
        if currpub is None:
            return None
        return currpub.section

    @property
    def component(self):
        """See IDistroReleaseSourcePackageRelease."""
        currpub = self.current_publishing_record
        if currpub is None:
            return None
        return currpub.component

    @property
    def publishing_history(self):
        """See IDistroReleaseSourcePackage."""
        return SourcePackagePublishingHistory.select("""
            distrorelease = %s AND
            sourcepackagerelease = %s
            """ % sqlvalues(self.distrorelease.id,
                            self.sourcepackagerelease.id),
            orderBy='-datecreated')

    @property
    def builds(self):
        """See IDistroReleaseSourcePackageRelease."""
        return Build.select("""
            Build.sourcepackagerelease = %s AND
            Build.distroarchrelease = DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s
            """ % sqlvalues(self.sourcepackagerelease.id,
                            self.distrorelease.id),
            orderBy='-datecreated',
            clauseTables=['distroarchrelease'])

    @property
    def files(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.files

    @property
    def binaries(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.binaries

    @property
    def builddepends(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.builddepends

    @property
    def builddependsindep(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.builddependsindep

    @property
    def architecturehintlist(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.architecturehintlist

    @property
    def dsc(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.dsc

    @property
    def format(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.format

    @property
    def urgency(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.urgency

    @property
    def changelog(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.changelog

    @property
    def uploaddistrorelease(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.uploaddistrorelease

    @property
    def dscsigningkey(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.dscsigningkey

    @property
    def dateuploaded(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.dateuploaded

    @property
    def sourcepackagename(self):
        """See ISourcePackageRelease."""
        return self.sourcepackagerelease.sourcepackagename

    def changeOverride(self, new_component=None, new_section=None):
        """See IDistroReleaseSourcePackageRelease."""

        # Check we have been asked to do something
        if new_component is None and new_section is None:
            raise AssertionError("changeOverride must be passed either a"
                                 " new component or new section.")

        # Retrieve current publishing info
        current = self.publishing_history[-1]

        # Check there is a change to make
        if new_component is None:
            new_component = current.component
        if new_section is None:
            new_section = current.section

        if (new_component == current.component and
            new_section == current.section):
            return

        SecureSourcePackagePublishingHistory(
            distrorelease=current.distrorelease,
            sourcepackagerelease=current.sourcepackagerelease,
            component=new_component,
            section=new_section,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=current.pocket,
            embargo=False,
        )

    def supersede(self):
        """See IDistroReleaseSourcePackageRelease."""

        current = self.publishing_history[-1]
        current = SecureSourcePackagePublishingHistory.get(current.id)
        current.status = PackagePublishingStatus.SUPERSEDED
        current.datesuperseded = UTC_NOW

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Published package interfaces."""

__metaclass__ = type

__all__ = [
    'IPublishedPackage',
    'IPublishedPackageSet',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')


class IPublishedPackage(Interface):
    """NOT A TABLE: this is a large database view which gives us a lot of
    de-normalised, but very useful information about packages which have
    been published in a distribution."""

    id = Attribute("The id of the packagepublishing record")
    distribution = Attribute("The distribution id")
    distroarchrelease = Attribute("The distroarchrelease.")
    distrorelease = Attribute("The distribution release id")
    distroreleasename = Attribute("The distribution release name")
    processorfamily = Attribute("The processor family id")
    processorfamilyname = Attribute("The processor family name")
    packagepublishingstatus = Attribute("The status of this published package")
    component = Attribute("The component in which the package has been published")
    section = Attribute("The section in which it is published.")
    binarypackagerelease = Attribute("The id of the binary package in question")
    binarypackagename = Attribute("The binary package name")
    binarypackagesummary = Attribute("The binary package summary")
    binarypackagedescription = Attribute("The binary package description")
    binarypackageversion = Attribute("The binary package version")
    build = Attribute("The build id")
    datebuilt = Attribute("The date this package was built or uploaded")
    sourcepackagerelease = Attribute("Source package release id")
    sourcepackagereleaseversion = Attribute("Source package release version")
    sourcepackagename = Attribute("Source package name")


class IPublishedPackageSet(Interface):
    """The set of packages that are published across all distributions"""

    def __iter__():
        """Iterate over all published packages."""

    def query(name=None, text=None, distribution=None, distrorelease=None,
              distroarchrelease=None, component=None):
        """Search through published packages returning those that meet the
        given criteria"""

    def findDepCandidate(name, distroarchrelease):
        """Return the package candidate within the distroarchrelease context.

        Return the PublishedPackage record by bynarypackagename or None if
        not found.
        """

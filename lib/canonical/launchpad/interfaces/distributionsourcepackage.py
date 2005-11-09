# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Source package in Distribution interfaces."""

__metaclass__ = type

__all__ = [
    'IDistributionSourcePackage',
    ]

from zope.interface import Interface, Attribute

from canonical.launchpad.interfaces.bug import IBugTarget
from canonical.launchpad.interfaces.tickettarget import ITicketTarget

class IDistributionSourcePackage(ITicketTarget, IBugTarget):

    distribution = Attribute("The distribution.")
    sourcepackagename = Attribute("The source package name.")

    name = Attribute("The source package name as text")
    displayname = Attribute("Display name for this package.")
    title = Attribute("Title for this package.")

    # XXX sabdfl 16/10/2005
    distro = Attribute("The distribution.")

    by_distroreleases = Attribute("Return a list of "
        "DistroReleaseSourcePackage "
        "objects, each representing this same source package in the "
        "releases of this distribution.")

    subscribers = Attribute("The subscribers to this package.")

    currentrelease = Attribute("""The latest published SourcePackageRelease
        of a source package with this name in the distribution or
        distrorelease, or None if no source package with that name is
        published in this distrorelease.""")

    releases = Attribute("The list of all releases of this source "
        "package in this distribution.")

    publishing_history = Attribute("Return a list of publishing "
        "records for this source package in this distribution.")

    binary_package_names = Attribute("A string of al the binary package "
        "names associated with this source package in this distribution.")

    def subscribe(person):
        """Subscribe a person to this package.

        :person: The person to subscribe. An IPerson.
        """

    def __getitem__(version):
        """Should map to getVersion."""

    def getVersion(version):
        """Return the a DistributionSourcePackageRelease with the given
        version, or None if there has never been a release with that
        version. in this Distribution.
        """

    def bugtasks(quantity=None):
        """Bug tasks on this source package, sorted newest first.

        If needed, you can limit the number of bugtasks you are interested
        in using the quantity parameter.
        """

    def __eq__(other):
        """IDistributionSourcePackage comparison method.

        Distro sourcepackages compare equal only if their distribution and
        sourcepackagename compare equal.
        """

    def __ne__(other):
        """IDistributionSourcePackage comparison method.

        Distro sourcepackages compare not equal if either of their distribution
        or sourcepackagename compare not equal.
        """

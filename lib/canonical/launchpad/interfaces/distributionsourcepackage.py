# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""Source package in Distribution interfaces."""

__metaclass__ = type

__all__ = [
    'DuplicateBugContactError',
    'DeleteBugContactError',
    'IDistributionSourcePackage',
    'IDistributionSourcePackageManageBugcontacts'
    ]

from zope.interface import Attribute, Interface
from zope.schema import Bool

from canonical.launchpad.interfaces.bugtarget import IBugTarget


class DuplicateBugContactError(Exception):
    """Raised when trying to add a package bug contact that already exists."""


class DeleteBugContactError(Exception):
    """Raised when an error occurred trying to delete a bug contact."""


class IDistributionSourcePackage(IBugTarget):

    distribution = Attribute("The distribution.")
    sourcepackagename = Attribute("The source package name.")

    name = Attribute("The source package name as text")
    displayname = Attribute("Display name for this package.")
    title = Attribute("Title for this package.")

    # XXX sabdfl 2005-10-16:
    distro = Attribute("The distribution.")

    subscribers = Attribute("The subscribers to this package.")

    currentrelease = Attribute(
        "The latest published SourcePackageRelease of a source package with "
        "this name in the distribution or distroseries, or None if no source "
        "package with that name is published in this distroseries.")

    releases = Attribute(
        "The list of all releases of this source package in this distribution.")

    publishing_history = Attribute(
        "Return a list of publishing records for this source package in this "
        "distribution.")

    current_publishing_records = Attribute(
        "Return a list of CURRENT publishing records for this source "
        "package in this distribution.")

    binary_package_names = Attribute(
        "A string of al the binary package names associated with this source "
        "package in this distribution.")

    bugcontacts = Attribute(
        "The list of people or teams that is explicitly Cc'd to all public "
        "bugs filed on this package.")

    def isBugContact(person):
        """Is person a bug contact for this package?

        If yes, the PackageBugContact is returned. Otherwise False is returned.
        """

    def __getitem__(version):
        """Should map to getVersion."""

    def getVersion(version):
        """Return the a DistributionSourcePackageRelease with the given
        version, or None if there has never been a release with that
        version in this distribution.
        """

    def get_distroseries_packages():
        """Return a list of DistroSeriesSourcePackage objects, each 
        representing this same source package in the serieses of this
        distribution.
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

    def addBugContact(person):
        """Add a bug contact for this package.

        :person: An IPerson or ITeam.
        """

    def removeBugContact(person):
        """Remove a bug contact from this package.

        :person: An IPerson or ITeam.
        """

    def subscribe(person):
        """Subscribe a person to this package.

        :person: The person to subscribe. An IPerson.
        """

class IDistributionSourcePackageManageBugcontacts(Interface):
    """Schema for the manage bug contacts form."""
    make_me_a_bugcontact = Bool(
        title=u"I want to receive all bugmail for this source package",
        required=False)

        

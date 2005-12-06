# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Binary package release in Distribution Architecture Release interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroArchReleaseBinaryPackageRelease',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.interfaces import IBinaryPackageRelease


class IDistroArchReleaseBinaryPackageRelease(IBinaryPackageRelease):
    """This is a BinaryPackageRelease-In-A-DistroArchRelease. It represents
    a real binary package release that has been uploaded to a distrorelease
    and published for that specific architecture.
    """

    distroarchrelease = Attribute("The distro architecture release.")
    binarypackagerelease = Attribute("The source package release.")

    name = Attribute("The binary package name as text")
    version = Attribute("The binary package version as text")
    displayname = Attribute("Display name for this package.")
    title = Attribute("Title for this package.")
    distribution = Attribute("The distribution.")
    distrorelease = Attribute("The distro release.")
    distributionsourcepackagerelease = Attribute("The source package in "
        "this distribution from which this package was built.")

    pocket = Attribute("The pocket in which this release is published, "
        "or None if it is not currently published.")

    status = Attribute("The current publishing status of this release "
        "of the binary package, in this distroarchrelease.")

    priority = Attribute("The current publishing priority of this release "
        "of the binary package, in this distroarchrelease.")

    section = Attribute("The section in which this package is published "
        "or None if it is not currently published.")

    component = Attribute("The component in which this package is "
        "published or None if it is not currently published.")

    publishing_history = Attribute("Return a list of publishing "
        "records for this binary package release in this release "
        "and this architecture, of the distribution.")

    current_publishing_record = Attribute("The current PUBLISHED record "
        "of this binary package release in this distro arch release, or "
        "None if there is not one.")


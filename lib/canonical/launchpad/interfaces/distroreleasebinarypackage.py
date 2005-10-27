
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for a Binary Package in a Distro Release."""

__metaclass__ = type

__all__ = [
    'IDistroReleaseBinaryPackage',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IDistroReleaseBinaryPackage(Interface):
    """A binary package in a distrorelease."""

    distrorelease = Attribute("The distrorelease.")
    binarypackagename = Attribute("The name of the binary package.")

    name = Attribute("The binary package name, as text.")
    cache = Attribute("The cache entry for this binary package name "
        "and distro release, or None if there isn't one.")
    summary = Attribute("The example summary of this, based on the "
        "cache. Since there may be a few, we try to use the latest "
        "one.")
    description = Attribute("An example description for this binary "
        "package. Again, there may be some variations based on "
        "versions and architectures in the distro release, so we try "
        "to use the newest one.")

    title = Attribute("Used for page layout.")
    distribution = Attribute("The distribution, based on the distrorelease")

    current_publishings = Attribute("The BinaryPackagePublishing records "
        "for this binary package name in this distrorelease.")



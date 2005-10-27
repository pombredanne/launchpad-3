
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Cache of Binary Package in DistroRelease details interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroReleasePackageCache',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

class IDistroReleasePackageCache(Interface):

    distrorelease = Attribute("The distrorelease.")
    binarypackagename = Attribute("The binary package name.")

    name = Attribute("The binary package name as text.")
    summary = Attribute("A single summary from one of the binary "
        "packages with this name in this distrorelease. The basic "
        "difficulty here is that two different architectures (or "
        "DistroArchReleases) might have binary packages with the "
        "same name but different summaries and descriptions. We "
        "can't know which is more important, so we single out "
        "one at random (well, alphabetically) and call that the "
        "summary for display purposes.")
    description = Attribute("A description, as per the summary.")
    summaries = Attribute("A concatenation of the package "
        "summaries for this binary package name in this distro release.")
    descriptions = Attribute("A concatenation of the descriptions "
        "of the binary packages from this binary package name in the "
        "distro release.")



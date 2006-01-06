# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Source package release in Distribution Release interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroReleaseSourcePackageRelease',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.interfaces.sourcepackagerelease import \
    ISourcePackageRelease

class IDistroReleaseSourcePackageRelease(ISourcePackageRelease):
    """This is a SourcePackageRelease-In-A-DistroRelease. It represents a
    real source package release that has been uploaded to a distrorelease.

    You can tell if it is still in the queue, and in which queue. You can
    ask it the dates of various events in its history in this
    distro-release. You can also ask it what pocket it is published in, if
    it has been published. Or which version superseded it, if it has been
    superseded.
    """

    distrorelease = Attribute("The distro release.")
    sourcepackagerelease = Attribute("The source package release.")

    name = Attribute("The source package name as text")
    displayname = Attribute("Display name for this package.")
    title = Attribute("Title for this package.")
    distribution = Attribute("The distribution.")
    pocket = Attribute("The pocket in which this release is published, "
        "or None if it is not currently published.")

    publishing_history = Attribute("Return a list of publishing "
        "records for this source package release in this release "
        "of the distribution.")

    builds = Attribute("The builds we have for this sourcepackage release "
        "specifically in this distribution. Note that binaries could "
        "be inherited from a parent distribution, not necessarily built "
        "here.")

    was_uploaded = Attribute("True or False, indicating whether or not "
        "a source package of this name was ever uploaded to this "
        "distrorelease.")

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Source package release in Distribution Series interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroSeriesSourcePackageRelease',
    ]

from zope.schema import Object
from zope.interface import Attribute

from canonical.launchpad import _
from canonical.launchpad.interfaces.sourcepackagerelease import (
    ISourcePackageRelease)
from canonical.launchpad.interfaces.librarian import (
    ILibraryFileAlias)


class IDistroSeriesSourcePackageRelease(ISourcePackageRelease):
    """This is a SourcePackageRelease-In-A-DistroSeries. It represents a
    real source package release that has been uploaded to a distroseries.

    You can tell if it is still in the queue, and in which queue. You can
    ask it the dates of various events in its history in this
    distroseries. You can also ask it what pocket it is published in, if
    it has been published. Or which version superseded it, if it has been
    superseded.
    """

    distroseries = Attribute("The distro series.")
    sourcepackagerelease = Attribute("The source package release.")

    name = Attribute("The source package name as text")
    displayname = Attribute("Display name for this package.")
    title = Attribute("Title for this package.")
    distribution = Attribute("The distribution.")
    pocket = Attribute("The pocket in which this release is published, "
        "or None if it is not currently published.")

    publishing_history = Attribute("Return a list of publishing "
        "records for this source package release in this series "
        "of the distribution.")

    builds = Attribute("The builds we have for this sourcepackage release "
        "specifically in this distribution. Note that binaries could "
        "be inherited from a parent distribution, not necessarily built "
        "here.")

    binaries = Attribute(
        "Return binaries resulted from this sourcepackagerelease and  "
        "published in this distroseries.")

    meta_binaries = Attribute(
        "Return meta binaries resulting from this sourcepackagerelease and "
        "published in this distroseries.")

    current_published = Attribute("is last SourcePackagePublishing record "
                                  "that is in PUBLISHED status.")

    version = Attribute("The version of the source package release.")

    changesfile = Object(
        title=_("Correspondent changesfile."), schema=ILibraryFileAlias,
        readonly=True)

    published_binaries = Attribute(
        "A list of published `DistroArchSeriesBinaryPackageRelease` for "
        "all relevant architectures.")

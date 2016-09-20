# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Source package release in Distribution interfaces."""

__metaclass__ = type

__all__ = [
    'IDistributionSourcePackageRelease',
    ]

from zope.interface import Attribute

from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease


class IDistributionSourcePackageRelease(ISourcePackageRelease):
    """This is a SourcePackageRelease-In-A-Distribution. It represents a
    real source package release that has been uploaded to a distribution.
    You can interrogate it for interesting information about its history in
    the distro.
    """

    distribution = Attribute("The distribution.")
    sourcepackagerelease = Attribute("The source package release.")

    sourcepackage = Attribute("Meta DistributionSourcePackage correspondont "
                              "to this release.")

    name = Attribute("The source package name as text")
    displayname = Attribute("Display name for this package.")
    title = Attribute("Title for this package.")

    publishing_history = Attribute("Return a list of publishing "
        "records for this source package release in this distribution.")

    builds = Attribute("The builds we have for this sourcepackage release "
        "specifically in this distribution. Note that binaries could "
        "be inherited from a parent distribution, not necessarily built "
        "here, but must be published in a main archive.")

    def getBuildsByArchTag(arch_tag):
        """Return the builds for this SPR on the given architecture."""

    sample_binary_packages = Attribute("A single binary package of each "
        "named package produced from this source package in this "
        "distribution. The are each of form DistroSeriesBinaryPackage.")

    def getBinariesForSeries(distroseries):
        """Return this SourcePackageRelease's binaries in this DistroSeries."""

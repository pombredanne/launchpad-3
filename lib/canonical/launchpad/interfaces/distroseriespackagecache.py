# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Cache of Binary Package in DistroSeries details interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroSeriesPackageCache',
    ]

from zope.interface import Interface, Attribute

class IDistroSeriesPackageCache(Interface):

    distroseries = Attribute("The distroseries.")
    binarypackagename = Attribute("The binary package name.")

    name = Attribute("The binary package name as text.")
    summary = Attribute("A single summary from one of the binary "
        "packages with this name in this distroseries. The basic "
        "difficulty here is that two different architectures (or "
        "DistroArchSeriess) might have binary packages with the "
        "same name but different summaries and descriptions. We "
        "can't know which is more important, so we single out "
        "one at random (well, alphabetically) and call that the "
        "summary for display purposes.")
    description = Attribute("A description, as per the summary.")
    summaries = Attribute("A concatenation of the package "
        "summaries for this binary package name in this distro series.")
    descriptions = Attribute("A concatenation of the descriptions "
        "of the binary packages from this binary package name in the "
        "distro series.")



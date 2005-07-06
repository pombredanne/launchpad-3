# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces related to publishing of source package releases."""

__metaclass__ = type

__all__ = [
    'ISourcePackageReleasePublishing',
    ]

from zope.schema import Int
from zope.interface import Attribute
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.interfaces.sourcepackagerelease import (
     ISourcePackageRelease)

_ = MessageIDFactory('launchpad')

class ISourcePackageReleasePublishing(ISourcePackageRelease):
    """
    Interface for the SQL VSourcePackageReleasePublishing View, which
    aggregates data from sourcepackagerelease, sourcepackagepublishing,
    sourcepackagename, component and distrorelease.
    """
    id = Int(title=_("ID"), required=True)
    publishingstatus = Attribute("The status of this publishing record")
    datepublished = Attribute("The date on which this record was published")
    publisheddistrorelease = Attribute(
        "The distro release into which this sourcepackage is published.")
    name = Attribute("The SourcePackage name")
    componentname = Attribute("The Component name")
    maintainer = Attribute("The maintainer of this package")

    sourcepackage = Attribute("The source package this is a release for")
    title = Attribute("Title")

    def __getitem__(version):
        """Get a SourcePackageRelease"""

    def traverse(name):
        """Traverse across a vsourcepakcagereleasepublishing in Launchpad.

        This looks for special URL items, like +rosetta, then goes on to
        traverse using __getitem__.
        """


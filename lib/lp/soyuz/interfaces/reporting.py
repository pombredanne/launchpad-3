# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'ILatestPersonSourcepackageReleaseCache',
    ]


from zope.interface import Attribute
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease


class ILatestPersonSourcepackageReleaseCache(ISourcePackageRelease):
    """Published source package release information for a person.

    The records represented by this object are the latest published source
    package releases for a given sourcepackage, distroseries, archive.
    """

    id = Attribute("The id of the associated SourcePackageRelease.")
    sourcepackagerelease = Attribute(
        "The SourcePackageRelease which this object represents.")
    publication = Attribute(
        "The publication record for the associated SourcePackageRelease.")

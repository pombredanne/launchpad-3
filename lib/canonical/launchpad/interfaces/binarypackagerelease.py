# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Binary package release interfaces."""

__metaclass__ = type

__all__ = [
    'IBinaryPackageRelease',
    'IBinaryPackageReleaseSet',
    ]

from zope.schema import Bool, Int, Text, TextLine, Datetime
from zope.interface import Interface, Attribute

from canonical.launchpad import _

from canonical.launchpad.validators.version import valid_debian_version


class IBinaryPackageRelease(Interface):
    id = Int(title=_('ID'), required=True)
    binarypackagename = Int(required=True)
    version = TextLine(required=True, constraint=valid_debian_version)
    summary = Text(required=True)
    description = Text(required=True)
    build = Int(required=True)
    binpackageformat = Int(required=True)
    component = Int(required=True)
    section = Int(required=True)
    priority = Int(required=False)
    shlibdeps = Text(required=False)
    depends = Text(required=False)
    recommends = Text(required=False)
    suggests = Text(required=False)
    conflicts = Text(required=False)
    replaces = Text(required=False)
    provides = Text(required=False)
    essential = Bool(required=False)
    installedsize = Int(required=False)
    architecturespecific = Bool(required=True)
    datecreated = Datetime(required=True, readonly=True)

    files = Attribute("Related list of IBinaryPackageFile entries")

    title = TextLine(required=True, readonly=True)
    name = Attribute("Binary Package Name")
    sourcepackagename = Attribute(
        "The name of the source package from where this binary was built.")

    # Properties.
    distributionsourcepackagerelease = Attribute(
        "The sourcepackage release in this distribution from which this "
        "binary was built.")

    is_new = Bool(
        title=_("New Binary."),
        description=_("True if there binary version was never published for "
                      "the architeture it was built for. False otherwise."))

    def lastversions():
        """Return the SUPERSEDED BinaryPackages in a DistroSeries
           that comes from the same SourcePackage"""

    def addFile(file):
        """Create a BinaryPackageFile record referencing this build
        and attach the provided library file alias (file).
        """

    def override(component=None, section=None, priority=None):
        """Uniform method to override binarypackagerelease attribute.

        All arguments are optional and can be set individually. A non-passed
        argument remains untouched.
        """

class IBinaryPackageReleaseSet(Interface):
    """A set of binary packages"""

    def findByNameInDistroSeries(distroseries, pattern,
                                  archtag=None, fti=False):
        """Returns a set of binarypackagereleases that matchs pattern
        inside a distroseries"""

    def getByNameInDistroSeries(distroseries, name):
        """Get an BinaryPackageRelease in a DistroSeries by its name"""


# Imports from zope
from zope.schema import Int, Text, TextLine
from zope.schema import Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class ISourcePackageInDistro(Interface):
    """A SourcePackage in Distro PG View"""
    id = Int(title=_("ID"), required=True)
    name = TextLine(title=_("Name"), required=True)
    distrorelease = Int(title=_("DistroRelease"), required=False)
    maintainer = Int(title=_("Maintainer"), required=True)
    title = TextLine(title=_("Title"), required=True)
    shortdesc = Text(title=_("Description"), required=True)
    description = Text(title=_("Description"), required=True)
    manifest = Int(title=_("Manifest"), required=False)
    distro = Int(title=_("Distribution"), required=False)
    sourcepackagename = Int(title=_("SourcePackage Name"), required=True)
    bugtasks = Attribute("bug tasks")
    product = Attribute("Product, or None")
    proposed = Attribute("A source package release with upload status of "
                         "PROPOSED, else None")

    def bugsCounter():
        """A bug counter widget for sourcepackage"""
    releases = Attribute("Set of releases tha this package is inside")
    current = Attribute("Set of current versions")
    lastversions = Attribute("set of lastversions")



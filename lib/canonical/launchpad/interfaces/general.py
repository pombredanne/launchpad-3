# Imports from zope
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class IbuilddepsSet(Interface):
    name = Attribute("Package name for a builddepends/builddependsindep")
    signal = Attribute("Dependence Signal e.g = >= <= <")
    version = Attribute("Package version for a builddepends/builddependsindep")

class ICurrentVersion(Interface):
    release = Attribute("The binary or source release object")
    currentversion = Attribute("Current version of A binary or source package")
    currentbuilds = Attribute(
        "The current builds for binary or source package")

class IDownloadURL(Interface):
    filename = Attribute("Downloadable Package name")
    fileurl = Attribute("Package full url")

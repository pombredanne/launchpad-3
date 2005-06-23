# XXX: IbuilddepsSet is named poorly.  These interfaces should not be in
#      something called 'general.py', and should have docstrings.
#      SteveAlexander, 2005-06-12


from zope.interface import Interface, Attribute


class IbuilddepsSet(Interface):
    name = Attribute("Package name for a builddepends/builddependsindep")
    signal = Attribute("Dependence Signal e.g = >= <= <")
    version = Attribute("Package version for a builddepends/builddependsindep")

class IDownloadURL(Interface):
    filename = Attribute("Downloadable Package name")
    fileurl = Attribute("Package full url")

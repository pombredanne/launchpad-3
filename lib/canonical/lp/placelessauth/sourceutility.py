from canonical.lp.placelessauth.interfaces import IPlacelessLoginSource
from zope.app.pluggableauth import BTreePrincipalSource
from zope.interface import implements
from zope.app import zapi

class Nothing:
    pass

class PlacelessLoginSource(BTreePrincipalSource):
    """ A demonstration implementation of a placeless principal source """

    implements(IPlacelessLoginSource)

    # the BTreePrincipalSource intends to be placeful, but we can use it
    # anyway with a little trickery
    __parent__ = Nothing()
    __parent__.earmark = Nothing()

    def getPrincipalByLogin(self, login):
        number = self._numbers_by_login[login]
        return self._principals_by_number[number]

        
    

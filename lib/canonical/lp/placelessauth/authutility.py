from canonical.lp.placelessauth.interfaces import IPlacelessAuthUtility, \
     IPlacelessLoginSource
from zope.interface import implements
from zope.app import zapi
from zope.app.security.interfaces import ILoginPassword
from zope.app.security.principalregistry import UnauthenticatedPrincipal


class PlacelessAuthUtility(object):
    """ An authentication service which holds no state aside from its
    ZCML configuration, implemented as a utility.  """

    implements(IPlacelessAuthUtility)

    def __init__(self):
        self.nobody = UnauthenticatedPrincipal('Anonymous', 'Anonymous',
                                  'Anonymous User')
        self.nobody.__parent__ = self

    def authenticate(self, request):
        """ See `IAuthenticationService`. """

        # XXX allow multiple placeless principal sources?
        login_src = zapi.getUtility(IPlacelessLoginSource)
        # XXX allow authentication scheme to be put into a view; for
        # now, use basic auth by specifying ILoginPassword.
        a = ILoginPassword(request, None)
        if a is not None:
            login = a.getLogin()
            if login is not None:
                p = login_src.getPrincipalByLogin(login)
                if p is not None:
                    password = a.getPassword()
                    if p.validate(password):
                        return p

    def unauthenticatedPrincipal(self):
        """ See `IAuthenticationService`. """
        return self.nobody

    def unauthorized(self, id, request):
        """ See `IAuthenticationService`. """
        # XXX replace hardcoded assumption of basic auth with a utility
        a = ILoginPassword(request)
        # XXX need to configure "realm" if we do configure from ZCML
        a.needLogin(realm="launchpad")

    def getPrincipal(self, id):
        """ See `IAuthenticationService`. """
        utility = zapi.getUtility(IPlacelessLoginSource)
        return utility.getPrincipal(id)

    def getPrincipals(self, name):
        """ See `IAuthenticationService`. """
        utility = zapi.getUtility(IPlacelessLoginSource)
        return utility.getPrincipals(name)

    def getPrincipalByLogin(self, login):
        """ See `IAuthenticationService`. """
        utility = zapi.getUtility(IPlacelessLoginSource)
        return utility.getPrincipalByLogin(login)

from canonical.lp.placelessauth.interfaces import IPlacelessAuthUtility, \
     IPlacelessLoginSource
from zope.interface import implements
from zope.app import zapi
from zope.app.session.interfaces import ISession
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

    def _authenticateUsingBasicAuth(self, credentials):
        login = credentials.getLogin()
        if login is not None:
            login_src = zapi.getUtility(IPlacelessLoginSource)
            principal = login_src.getPrincipalByLogin(login)
            if principal is not None:
                password = credentials.getPassword()
                if principal.validate(password):
                    return principal

    def _authenticateUsingCookieAuth(self, request):
        session = ISession(request)
        authdata = session['launchpad.authenticateduser']
        if authdata.get('personid') is None:
            return None
        else:
            personid = authdata['personid']
            login_src = zapi.getUtility(IPlacelessLoginSource)
            return login_src.getPrincipal(personid)

    def authenticate(self, request):
        """ See `IAuthenticationService`. """
        # To avoid confusion (hopefully), basic auth trumps cookie auth
        # totally, and all the time.  If there is any basic auth at all,
        # then cookie auth won't even be considered.

        # XXX allow authentication scheme to be put into a view; for
        # now, use basic auth by specifying ILoginPassword.
        credentials = ILoginPassword(request, None)
        if credentials is not None and credentials.getLogin() is not None:
            return self._authenticateUsingBasicAuth(credentials)
        else:
            # Hack to make us not even think of using a session if there
            # isn't already a cookie there.
            if request.cookies.get('launchpad') is not None:
                return self._authenticateUsingCookieAuth(request)

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

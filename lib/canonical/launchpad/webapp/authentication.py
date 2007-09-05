# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import binascii
import random
import sha

from zope.interface import implements
from zope.component import getUtility
from zope.event import notify

from zope.security.proxy import removeSecurityProxy

from zope.app.session.interfaces import ISession
from zope.app.security.interfaces import ILoginPassword
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.app.security.principalregistry import UnauthenticatedPrincipal

from canonical.config import config
from canonical.launchpad.interfaces import IPersonSet, IPasswordEncryptor
from canonical.launchpad.webapp.interfaces import ILoggedOutEvent
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal
from canonical.launchpad.webapp.interfaces import BasicAuthLoggedInEvent
from canonical.launchpad.webapp.interfaces import (
        CookieAuthPrincipalIdentifiedEvent)


def handle(event):
    """Event handler for traversal and login/logout events that performs
    authentication.

    Each of these events has a `request` attribute.
    """
    request = event.request
    if not ILoggedOutEvent.providedBy(event):
        if not IUnauthenticatedPrincipal.providedBy(request.principal):
            # We've already got an authenticated user. There's nothing to do.
            # Note that beforeTraversal guarentees that user is not None.
            return

    auth_utility = getUtility(IPlacelessAuthUtility)
    principal = auth_utility.authenticate(request)
    if principal is None:
        principal = auth_utility.unauthenticatedPrincipal()
        if principal is not None:
            request.setPrincipal(principal)


class PlacelessAuthUtility:
    """An authentication service which holds no state aside from its
    ZCML configuration, implemented as a utility.
    """
    implements(IPlacelessAuthUtility)

    def __init__(self):
        self.nobody = UnauthenticatedPrincipal(
            'Anonymous', 'Anonymous', 'Anonymous User')
        self.nobody.__parent__ = self

    def _authenticateUsingBasicAuth(self, credentials, request):
        login = credentials.getLogin()
        if login is not None:
            login_src = getUtility(IPlacelessLoginSource)
            principal = login_src.getPrincipalByLogin(login)
            if principal is not None:
                person = getUtility(IPersonSet).get(principal.id)
                if person.is_valid_person:
                    password = credentials.getPassword()
                    if principal.validate(password):
                        request.setPrincipal(principal)
                        # We send a LoggedInEvent here, when the
                        # cookie auth below sends a PrincipalIdentified,
                        # as the login form is never visited for BasicAuth.
                        # This we treat each request as a seperate login/logout
                        notify(BasicAuthLoggedInEvent(
                            request, login, principal
                            ))
                        return principal

    def _authenticateUsingCookieAuth(self, request):
        session = ISession(request)
        authdata = session['launchpad.authenticateduser']
        if authdata.get('personid') is None:
            return None
        else:
            personid = authdata['personid']
            login_src = getUtility(IPlacelessLoginSource)
            # Note, not notifying a LoggedInEvent here as for session-based
            # auth the login occurs when the login form is submitted, not
            # on each request.
            principal = login_src.getPrincipal(personid)
            if principal is None:
                # XXX Stuart Bishop 2006-05-26 bug=33427:
                # User is authenticated in session, but principal is not"
                # available in login source. This happens when account has
                # become invalid for some reason, such as being merged.
                return None
            elif getUtility(IPersonSet).get(principal.id).is_valid_person:
                request.setPrincipal(principal)
                login = authdata['login']
                assert login, 'login is %s!' % repr(login)
                notify(CookieAuthPrincipalIdentifiedEvent(
                    principal, request, login
                    ))
                return principal
            else:
                return None

    def authenticate(self, request):
        """See IAuthenticationService."""
        # To avoid confusion (hopefully), basic auth trumps cookie auth
        # totally, and all the time.  If there is any basic auth at all,
        # then cookie auth won't even be considered.

        # XXX daniels 2004-12-14: allow authentication scheme to be put into
        #     a view; for now, use basic auth by specifying ILoginPassword.
        credentials = ILoginPassword(request, None)
        if credentials is not None and credentials.getLogin() is not None:
            return self._authenticateUsingBasicAuth(credentials, request)
        else:
            # Hack to make us not even think of using a session if there
            # isn't already a cookie in the request, or one waiting to be
            # set in the response.
            cookie_name = config.launchpad.session.cookie
            if (request.cookies.get(cookie_name) is not None or
                request.response.getCookie(cookie_name) is not None):
                return self._authenticateUsingCookieAuth(request)
            else:
                return None

    def unauthenticatedPrincipal(self):
        """See IAuthenticationService."""
        return self.nobody

    def unauthorized(self, id, request):
        """See IAuthenticationService."""
        a = ILoginPassword(request)
        # TODO maybe configure the realm from zconfigure.
        a.needLogin(realm="launchpad")

    def getPrincipal(self, id):
        """See IAuthenticationService."""
        utility = getUtility(IPlacelessLoginSource)
        return utility.getPrincipal(id)

    def getPrincipals(self, name):
        """See IAuthenticationService."""
        utility = getUtility(IPlacelessLoginSource)
        return utility.getPrincipals(name)

    def getPrincipalByLogin(self, login):
        """See IAuthenticationService."""
        utility = getUtility(IPlacelessLoginSource)
        return utility.getPrincipalByLogin(login)


class SSHADigestEncryptor:
    """SSHA is a modification of the SHA digest scheme with a salt
    starting at byte 20 of the base64-encoded string.
    """
    implements(IPasswordEncryptor)

    # Source: http://developer.netscape.com/docs/technote/ldap/pass_sha.html

    saltLength = 20

    def generate_salt(self):
        # Salt can be any length, but not more than about 37 characters
        # because of limitations of the binascii module.
        # All 256 characters are available.
        salt = ''
        for n in range(self.saltLength):
            salt += chr(random.randrange(256))
        return salt

    def encrypt(self, plaintext, salt=None):
        plaintext = str(plaintext)
        if salt is None:
            salt = self.generate_salt()
        v = binascii.b2a_base64(sha.new(plaintext + salt).digest() + salt)
        return v[:-1]

    def validate(self, plaintext, encrypted):
        encrypted = str(encrypted)
        plaintext = str(plaintext)
        try:
            ref = binascii.a2b_base64(encrypted)
        except binascii.Error:
            # Not valid base64.
            return False
        salt = ref[20:]
        v = binascii.b2a_base64(sha.new(plaintext + salt).digest() + salt)[:-1]
        pw1 = (v or '').strip()
        pw2 = (encrypted or '').strip()
        return pw1 == pw2

class LaunchpadLoginSource:
    """A login source that uses the launchpad SQL database to look up
    principal information.
    """
    implements(IPlacelessLoginSource)

    def getPrincipal(self, id):
        """Return a principal based on the person with the provided id.

        Note that we currently need to be able to retrieve principals for
        invalid People, as the login machinery needs the principal to
        validate the password against so it may then email a validation
        request to the user and inform them it has done so.
        """
        person = getUtility(IPersonSet).get(id)
        if person is not None:
            return self._principalForPerson(person)
        else:
            return None

    def getPrincipals(self, name):
        raise NotImplementedError

    def getPrincipalByLogin(self, login):
        """Return a principal based on the person with the email address
        signified by "login".

        Note that we currently need to be able to retrieve principals for
        invalid People, as the login machinery needs the principal to
        validate the password against so it may then email a validation
        request to the user and inform them it has done so.
        """
        person = getUtility(IPersonSet).getByEmail(login)
        if person is not None:
            return self._principalForPerson(person)
        else:
            return None

    def _principalForPerson(self, person):
        person = removeSecurityProxy(person)
        principal = LaunchpadPrincipal(
            person.id,
            person.browsername,
            person.displayname,
            person.password,
            )
        principal.__parent__ = self
        return principal

# Fake a containment heirarchy because Zope3 is on crack
authService = PlacelessAuthUtility()
loginSource = LaunchpadLoginSource()
loginSource.__parent__ = authService

class LaunchpadPrincipal:

    implements(ILaunchpadPrincipal)

    def __init__(self, id, title, description, pwd=None):
        self.id = id
        self.title = title
        self.description = description
        self.__pwd = pwd

    def getLogin(self):
        return self.title

    def validate(self, pw):
        encryptor = getUtility(IPasswordEncryptor)
        pw1 = (pw or '').strip()
        pw2 = (self.__pwd or '').strip()
        return encryptor.validate(pw1, pw2)



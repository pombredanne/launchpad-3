# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import Interface, Attribute, implements

from zope.app.security.interfaces import IAuthenticationService, IPrincipal
from zope.app.pluggableauth.interfaces import IPrincipalSource


class IPrincipalIdentifiedEvent(Interface):
    """An event that is sent after a principal has been recovered from the
    request's credentials.
    """
    principal = Attribute('The principal')
    request = Attribute('The request')

class ILoggedInEvent(Interface):
    """An event that is sent after someone has logged in.

    Exactly what this means will vary according to the type of login,
    primarily as to whether it is per-request or session-based.
    """
    request = Attribute('The request')
    login = Attribute(
        'The login id that was used.  For example, an email address.')


class CookieAuthLoggedInEvent:
    implements(ILoggedInEvent)
    def __init__(self, request, login):
        self.request = request
        self.login = login

class CookieAuthPrincipalIdentifiedEvent:
    implements(IPrincipalIdentifiedEvent)
    def __init__(self, principal, request):
        self.principal = principal
        self.request = request

class BasicAuthLoggedInEvent:
    implements(ILoggedInEvent, IPrincipalIdentifiedEvent)
    def __init__(self, request, login, principal):
        # these one from ILoggedInEvent
        self.login = login
        # this one from IPrincipalIdentifiedEvent
        self.principal = principal
        # this one from ILoggedInEvent and IPrincipalIdentifiedEvent
        self.request = request

class ILoggedOutEvent(Interface):
    """An event which gets sent after someone has logged out via a form."""

class LoggedOutEvent:
    implements(ILoggedOutEvent)
    def __init__(self, request):
        self.request = request


class IPlacelessAuthUtility(IAuthenticationService):
    """This is a marker interface for a utility that supplies the interface
    of the authentication service placelessly, with the addition of
    a method to allow the acquisition of a principal using his
    login name.
    """

    def getPrincipalByLogin(login):
        """Return a principal based on his login name."""


class IPlacelessLoginSource(IPrincipalSource):
    """This is a principal source that has no place.  It extends
    the pluggable auth IPrincipalSource interface, allowing for disparity
    between the user id and login name.
    """

    def getPrincipalByLogin(login):
        """Return a principal based on his login name."""

    def getPrincipals(name):
        """Not implemented.

        Get principals with matching names.
        See zope.app.pluggableauth.interfaces.IPrincipalSource
        """

class ILaunchpadPrincipal(IPrincipal):
    """Marker interface for launchpad principals.

    This is used for the launchpad.AnyPerson permission.
    """


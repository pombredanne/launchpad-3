# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import Interface, implements

from zope.app.security.interfaces import IAuthenticationService, IPrincipal
from zope.app.pluggableauth.interfaces import IPrincipalSource


class ILoggedInEvent(Interface):
    """An event which gets sent after someone has logged in via a form."""

class LoggedInEvent:
    implements(ILoggedInEvent)
    def __init__(self, request):
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


from zope.app import zapi
from canonical.lp.placelessauth.interfaces import IPlacelessAuthUtility
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from canonical.launchpad.webapp.login import ILoggedOutEvent


def handle(event):
    # A single instance of a PlacelessAuthUtility will be registered via ZCML.
    # We need to get this instance and call its authenticate method with the
    # request attached to this event.
    request = event.request

    if not ILoggedOutEvent.providedBy(event):
        if not IUnauthenticatedPrincipal.providedBy(request.principal):
            # We've already got an authenticated user. There's nothing to do.
            # Note that beforeTraversal guarentees that user is not None.
            return

    auth_utility = zapi.getUtility(IPlacelessAuthUtility)
    principal = auth_utility.authenticate(request)
    if principal is None:
        principal = auth_utility.unauthenticatedPrincipal()
        if principal is None:
            return
    request.setPrincipal(principal)
    

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.component import getUtility
from canonical.launchpad.helpers import setupInteraction
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility

ANONYMOUS = 'launchpad.anonymous'

def login(email, participation=None):
    """Simulates a login, using the specified email.

    If the canonical.launchpad.ftests.ANONYMOUS constant is supplied 
    as the email, you'll be logged in as the anonymous user.

    You can optionally pass in a participation to be used.  If no participation
    is given, a MockParticipation is used.

    The participation passed in must allow setting of its principal.
    """
    authutil = getUtility(IPlacelessAuthUtility)

    if email == ANONYMOUS:
        principal = authutil.unauthenticatedPrincipal()
    else:
        principal = authutil.getPrincipalByLogin(email)

    setupInteraction(principal, login=email, participation=participation)

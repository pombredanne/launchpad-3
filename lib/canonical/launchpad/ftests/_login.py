# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.component import getUtility
from zope.security.management import queryInteraction, endInteraction
from canonical.launchpad.helpers import setupInteraction
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility

__all__ = ['login', 'logout', 'ANONYMOUS']

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

    # Bootstrap the interaction.
    if not queryInteraction():
        setupInteraction(authutil.unauthenticatedPrincipal())

    if email == ANONYMOUS:
        principal = authutil.unauthenticatedPrincipal()
    else:
        principal = authutil.getPrincipalByLogin(email)
        assert principal is not None, "Invalid login"

    setupInteraction(principal, login=email, participation=participation)

def logout():
    """Tear down after login(...), ending the current interaction.

    Note that this is done automatically in
    canonical.launchpad.ftest.LaunchpadFunctionalTestCase's tearDown method so
    you generally won't need to call this.
    """
    endInteraction()

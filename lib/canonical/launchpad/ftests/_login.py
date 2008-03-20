# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# We like global statements!
# pylint: disable-msg=W0602,W0603
__metaclass__ = type

from zope.component import getUtility
from zope.security.management import endInteraction
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import setupInteraction

__all__ = ['login', 'logout', 'ANONYMOUS', 'is_logged_in']


ANONYMOUS = 'launchpad.anonymous'

_logged_in = False

def is_logged_in():
    global _logged_in
    return _logged_in

def login(email, participation=None):
    """Simulates a login, using the specified email.

    If the canonical.launchpad.ftests.ANONYMOUS constant is supplied
    as the email, you'll be logged in as the anonymous user.

    You can optionally pass in a participation to be used.  If no
    participation is given, a MockParticipation is used.

    If the participation provides IPublicationRequest, it must implement
    setPrincipal(), otherwise it must allow setting its principal attribute.
    """
    global _logged_in
    _logged_in = True
    authutil = getUtility(IPlacelessAuthUtility)


    if email != ANONYMOUS:
        # Create an anonymous interaction first because this calls
        # IPersonSet.getByEmail() and since this is security wrapped, it needs
        # an interaction available.
        setupInteraction(authutil.unauthenticatedPrincipal())
        principal = authutil.getPrincipalByLogin(email)
        assert principal is not None, "Invalid login"
    else:
        principal = authutil.unauthenticatedPrincipal()

    setupInteraction(principal, login=email, participation=participation)


def logout():
    """Tear down after login(...), ending the current interaction.

    Note that this is done automatically in
    canonical.launchpad.ftest.LaunchpadFunctionalTestCase's tearDown method so
    you generally won't need to call this.
    """
    global _logged_in
    _logged_in = False
    endInteraction()


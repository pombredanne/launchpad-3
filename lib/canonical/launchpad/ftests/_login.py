# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import zope.security.management
from zope.interface import implements
from zope.app.tests import ztapi
from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchBag, IPerson
from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource

class MockLaunchBag(object):
    implements(ILaunchBag)
    def __init__(self, login=None, user=None):
        self.login = login
        self.user = user

class MockParticipation:
    interaction = None
    principal = None

class MockPrincipal:
    def __init__(self, id):
        self.id = id
        self.groups = []

ANONYMOUS = 'launchpad.anonymous'

def login(email):
    """Simulates a login, using the specified email.
    
    If the canonical.launchpad.ftests.ANONYMOUS constant is supplied 
    as the email, you'll be logged in as the anonymous user.
    """
    # First end any running interaction, and start a new one
    zope.security.management.endInteraction()
    participation = MockParticipation()
    zope.security.management.newInteraction(participation)

    if email == ANONYMOUS:
        principal = MockPrincipal(ANONYMOUS)
        launchbag = MockLaunchBag()
    else:
        login_src = getUtility(IPlacelessLoginSource)
        principal = login_src.getPrincipalByLogin(email)
        user = IPerson(principal)
        launchbag = MockLaunchBag(email, user)

    participation.principal = principal
    ztapi.provideUtility(ILaunchBag, launchbag)

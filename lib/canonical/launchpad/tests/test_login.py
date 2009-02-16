# Copyright 2009 Canonical Ltd.  All rights reserved.

from datetime import datetime
import unittest

from zope.component import getUtility
from zope.event import notify
from zope.session.interfaces import ISession

from canonical.config import config

from canonical.launchpad.ftests import login
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.authentication import LaunchpadPrincipal
from canonical.launchpad.webapp.interfaces import (
    CookieAuthLoggedInEvent, IPlacelessAuthUtility)
from canonical.launchpad.webapp.login import logInPerson, logoutPerson
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadFunctionalLayer


class TestLoginAndLogout(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.request = LaunchpadTestRequest()
        person = self.factory.makePerson('foo.bar@example.com')
        self.principal = LaunchpadPrincipal(
            person.account.id, person.browsername,
            person.displayname, person)

    def test_logging_in_and_logging_out(self):
        # A test showing that we can authenticate the request after
        # logInPerson() is called, and after logoutPerson() we can no longer
        # authenticate it.

        # This is to setup an interaction so that we can call logInPerson
        # below.
        login('foo.bar@example.com')

        logInPerson(self.request, self.principal, 'foo.bar@example.com')
        session = ISession(self.request)
        # logInPerson() stores the account ID in a variable named 'accountid'.
        self.failUnlessEqual(
            session['launchpad.authenticateduser']['accountid'],
            self.principal.id)

        # This is so that the authenticate() call below uses cookie auth.
        self.request.response.setCookie(
            config.launchpad_session.cookie, 'xxx')

        principal = getUtility(IPlacelessAuthUtility).authenticate(
            self.request)
        self.failUnlessEqual(self.principal.id, principal.id)

        logoutPerson(self.request)

        principal = getUtility(IPlacelessAuthUtility).authenticate(
            self.request)
        self.failUnless(principal is None)

    def test_logging_in_and_logging_out_the_old_way(self):
        # A test showing that we can authenticate a request that had the
        # person/account ID stored in the 'personid' session variable instead
        # of 'accountid' -- where it's stored by logInPerson(). Also shows
        # that after logoutPerson() we can no longer authenticate it.
        # This is just for backwards compatibility.

        # This is to setup an interaction so that we can call logInPerson
        # below.
        login('foo.bar@example.com')

        session = ISession(self.request)
        authdata = session['launchpad.authenticateduser']
        self.request.setPrincipal(self.principal)
        authdata['personid'] = self.principal.id
        authdata['logintime'] = datetime.utcnow()
        authdata['login'] = 'foo.bar@example.com'
        notify(CookieAuthLoggedInEvent(self.request, 'foo.bar@example.com'))

        # This is so that the authenticate() call below uses cookie auth.
        self.request.response.setCookie(
            config.launchpad_session.cookie, 'xxx')

        principal = getUtility(IPlacelessAuthUtility).authenticate(
            self.request)
        self.failUnlessEqual(self.principal.id, principal.id)

        logoutPerson(self.request)

        principal = getUtility(IPlacelessAuthUtility).authenticate(
            self.request)
        self.failUnless(principal is None)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

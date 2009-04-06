# Copyright 2009 Canonical Ltd.  All rights reserved.

from datetime import datetime
import unittest

from zope.component import getUtility
from zope.event import notify
from zope.session.interfaces import ISession

from canonical.config import config

from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.launchpad.interfaces.account import (
    AccountCreationRationale, IAccountSet)
from lp.registry.interfaces.person import IPerson
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.authentication import LaunchpadPrincipal
from canonical.launchpad.webapp.interfaces import (
    CookieAuthLoggedInEvent, ILaunchpadPrincipal, IPlacelessAuthUtility)
from canonical.launchpad.webapp.login import (
    logInPrincipal, logInPrincipalAndMaybeCreatePerson, logoutPerson)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import DatabaseFunctionalLayer


class TestLoginAndLogout(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.request = LaunchpadTestRequest()
        # We create an account without a Person here just to make sure the
        # person and account created later don't end up with the same IDs,
        # which could happen since they're both sequential.
        # We need them to be different for one of our tests here.
        dummy_account = getUtility(IAccountSet).new(
            AccountCreationRationale.UNKNOWN, 'Dummy name')
        person = self.factory.makePerson('foo.bar@example.com')
        self.failIfEqual(person.id, person.account.id)
        self.principal = LaunchpadPrincipal(
            person.account.id, person.browsername,
            person.displayname, person)

    def test_logging_in_and_logging_out(self):
        # A test showing that we can authenticate the request after
        # logInPrincipal() is called, and after logoutPerson() we can no
        # longer authenticate it.

        # This is to setup an interaction so that we can call logInPrincipal
        # below.
        login('foo.bar@example.com')

        logInPrincipal(self.request, self.principal, 'foo.bar@example.com')
        session = ISession(self.request)
        # logInPrincipal() stores the account ID in a variable named
        # 'accountid'.
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
        # of 'accountid' -- where it's stored by logInPrincipal(). Also shows
        # that after logoutPerson() we can no longer authenticate it.
        # This is just for backwards compatibility.

        # This is to setup an interaction so that we can do the same thing
        # that's done by logInPrincipal() below.
        login('foo.bar@example.com')

        session = ISession(self.request)
        authdata = session['launchpad.authenticateduser']
        self.request.setPrincipal(self.principal)
        authdata['personid'] = self.principal.person.id
        authdata['logintime'] = datetime.utcnow()
        authdata['login'] = 'foo.bar@example.com'
        notify(CookieAuthLoggedInEvent(self.request, 'foo.bar@example.com'))

        # This is so that the authenticate() call below uses cookie auth.
        self.request.response.setCookie(
            config.launchpad_session.cookie, 'xxx')

        principal = getUtility(IPlacelessAuthUtility).authenticate(
            self.request)
        self.failUnlessEqual(self.principal.id, principal.id)
        self.failUnlessEqual(self.principal.person, principal.person)

        logoutPerson(self.request)

        principal = getUtility(IPlacelessAuthUtility).authenticate(
            self.request)
        self.failUnless(principal is None)


class TestLoggingInWithPersonlessAccount(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.request = LaunchpadTestRequest()
        login(ANONYMOUS)
        account_set = getUtility(IAccountSet)
        account, email = account_set.createAccountAndEmail(
            'foo@example.com', AccountCreationRationale.UNKNOWN,
            'Display name', 'password')
        self.principal = LaunchpadPrincipal(
            account.id, account.displayname, account.displayname, account)
        login('foo@example.com')

    def test_logInPrincipal(self):
        # logInPrincipal() will log the given principal in and not worry about
        # its lack of an associated Person.
        logInPrincipal(self.request, self.principal, 'foo@example.com')

        # This is so that the authenticate() call below uses cookie auth.
        self.request.response.setCookie(
            config.launchpad_session.cookie, 'xxx')

        principal = getUtility(IPlacelessAuthUtility).authenticate(
            self.request)
        self.failUnless(ILaunchpadPrincipal.providedBy(principal))
        self.failUnless(principal.person is None)

    def test_logInPrincipalAndMaybeCreatePerson(self):
        # logInPrincipalAndMaybeCreatePerson() will log the given principal in
        # and create a Person entry associated with it if one doesn't exist
        # already.
        logInPrincipalAndMaybeCreatePerson(
            self.request, self.principal, 'foo@example.com')

        # This is so that the authenticate() call below uses cookie auth.
        self.request.response.setCookie(
            config.launchpad_session.cookie, 'xxx')

        principal = getUtility(IPlacelessAuthUtility).authenticate(
            self.request)
        self.failUnless(ILaunchpadPrincipal.providedBy(principal))
        person = IPerson(principal.account)
        self.failUnless(IPerson.providedBy(person))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

# Copyright 2007-2009 Canonical Ltd.  All rights reserved.

"""Test harness for Login Service related unit tests."""

__metaclass__ = type

__all__ = []

from datetime import datetime, timedelta
from urllib import urlencode
import unittest

from openid.message import Message, OPENID2_NS
from openid.server.server import OpenIDResponse

from zope.component import getUtility
from zope.session.interfaces import ISession
from zope.testing import doctest

from canonical.launchpad.browser.openidserver import OpenIDMixin
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.database.openidserver import OpenIDAuthorization
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.openidserver import IOpenIDRPConfigSet
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.launchpad.testing.pages import setupBrowser
from canonical.launchpad.webapp.dbpolicy import SSODatabasePolicy
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import DatabaseFunctionalLayer


class SSODatabasePolicyTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        self.dbpolicy = SSODatabasePolicy(LaunchpadTestRequest())
        self.dbpolicy.beforeTraversal()
        super(SSODatabasePolicyTestCase, self).setUp()

    def tearDown(self):
        super(SSODatabasePolicyTestCase, self).tearDown()
        self.dbpolicy.afterCall()


class SimpleRegistrationTestCase(SSODatabasePolicyTestCase):
    """Tests for Simple Registration helpers in OpenIDMixin"""

    def setUp(self):
        login(ANONYMOUS)
        super(SSODatabasePolicyTestCase, self).setUp()

    def tearDown(self):
        super(SSODatabasePolicyTestCase, self).tearDown()
        logout()

    def test_sreg_field_names(self):
        # Test that sreg_field_names returns an appropriate value
        # according to both the OpenID request and the policy defined
        # for the RP.
        getUtility(IOpenIDRPConfigSet).new(
            trust_root='fake-trust-root', displayname='Fake Trust Root',
            description='Description',
            allowed_sreg=['email', 'fullname', 'postcode'])
        class FieldNameTest(OpenIDMixin):
            class openid_request:
                trust_root = 'fake-trust-root'
                message = Message.fromPostArgs({
                    'openid.sreg.required': 'email,country,nickname',
                    'openid.sreg.optional': 'fullname'})
        view = FieldNameTest(None, None)
        # Note that country and nickname are not returned since they
        # are not included in the policy.  Similarly, postcode is not
        # returned since it was not requested.  The field names are
        # returned in a fixed order.
        self.assertEqual(view.sreg_field_names, ['fullname', 'email'])

    def test_sreg_fields(self):
        # Test that user details are extracted correctly.
        class FieldValueTest(OpenIDMixin):
            account = getUtility(IPersonSet).getByEmail('david@canonical.com')
            sreg_field_names = [
                'fullname', 'nickname', 'email', 'timezone',
                'x_address1', 'x_address2', 'x_city', 'x_province',
                'country', 'postcode', 'x_phone', 'x_organization']
        view = FieldValueTest(None, None)
        self.assertEqual(view.sreg_fields, [
            ('fullname', u'David Allouche'),
            ('nickname', u'ddaa'),
            ('email', u'david.allouche@canonical.com'),
            ('timezone', u'UTC'),
            ('x_address1', u'Velvet Zephyr Woods'),
            ('x_address2', u'5423'),
            ('x_city', u'whatever'),
            ('x_province', u'not mandatory'),
            ('country', u'France'),
            ('postcode', u'999432423'),
            ('x_phone', u'+55 16 3374-2027')])

    def test_sreg_fields_no_shipping(self):
        # Test that user details are extracted correctly when there is
        # no previous successful shipit request.
        person = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')
        self.assertEqual(person.lastShippedRequest(), None)
        class FieldValueTest(OpenIDMixin):
            account = person.account
            sreg_field_names = [
                'fullname', 'nickname', 'email', 'timezone',
                'x_address1', 'x_address2', 'x_city', 'x_province',
                'country', 'postcode', 'x_phone', 'x_organization']
        view = FieldValueTest(None, None)
        self.assertEqual(view.sreg_fields, [
            ('fullname', u'No Privileges Person'),
            ('nickname', u'no-priv'),
            ('email', u'no-priv@canonical.com'),
            ('timezone', u'Europe/Paris')])


class PreAuthorizeRPViewTestCase(SSODatabasePolicyTestCase):
    """Test for the PreAuthorizeRPView."""

    def test_pre_authorize_works_with_slave_store(self):
        """
        By using a browser using basic authorization, we make sure
        that the slave will be used. The pre-authorization acceptance test
        uses the login form and thus uses the MASTER store.
        """

        browser = setupBrowser('Basic no-priv@canonical.com:test')
        args = urlencode({
            'trust_root': 'http://launchpad.dev/',
            'callback': 'http://launchpad.dev/people/+me'})
        browser.open(
            'http://openid.launchpad.dev/+pre-authorize-rp?%s' % args)

        login(ANONYMOUS)
        no_priv = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')

        # We do not use the isAuthorized API because we don't know the client
        # id used by browser, since no cookie were used.
        self.failUnless(OpenIDAuthorization.selectOneBy(
            accountID=no_priv.accountID, trust_root='http://launchpad.dev/'),
            "Pre-authorization record wasn't created.")


class FakeOpenIdRequest:
    """A fake openid request for unit testing.

    It only provides the message attribute. And that one only provides
    the getArgs() method which will return canned data.

    Whatever is in the args attribute.
    """

    def __init__(self):
        self.args = {}

    @property
    def message(self):
        return self

    def getArgs(self, namespace):
        return self.args


class OpenIDMixin_shouldReauthenticate_TestCase(SSODatabasePolicyTestCase):
    """Test cases for the shouldReauthenticate() period."""

    def setUp(self):
        """Sets up a very simple openid_mixin with a FakeOpenIdRequest.

        The user is set-up to have logged 90 days ago.
        """
        class ShouldReauthenticateTest(OpenIDMixin):
            # Must create this class so that we can override account, which is
            # a @property on OpenIDMixin.
            account = object()
        self.request = LaunchpadTestRequest(
            SERVER_URL='http://openid.launchpad.net/+openid')
        login("test@canonical.com", self.request)
        self.openid_mixin = ShouldReauthenticateTest(None, self.request)
        self.openid_mixin.request = self.request
        self.openid_request = FakeOpenIdRequest()
        self.openid_mixin.openid_request = self.openid_request
        self.authdata = ISession(self.request)['launchpad.authenticateduser']
        self.authdata['logintime'] = datetime.utcnow() - timedelta(days=90)

    def tearDown(self):
        logout()

    def test_should_be_False_when_param_not_used(self):
        """If the extension isn't present in the request, and the user is
        logged in, it should be False."""
        self.assertEquals(False, self.openid_mixin.shouldReauthenticate())

    def test_should_be_True_with_zero(self):
        """If the maximum delta is 0, the user must re-authenticate."""
        self.openid_request.args['max_auth_age'] = '0'
        self.assertEquals(True, self.openid_mixin.shouldReauthenticate())

    def test_should_be_True_with_negative(self):
        """If the maximum delta is below zero, the user must re-authenticate.
        """
        self.openid_request.args['max_auth_age'] = '-1'
        self.assertEquals(True, self.openid_mixin.shouldReauthenticate())

    def test_should_ignore_invalid_param(self):
        """If the maximum delta is not an integer, it's like if the parameter
        wasn't used. That's mainly because python-openid hides that fact
        from us."""
        self.openid_request.args['max_auth_age'] = 'not a number'
        self.assertEquals(False, self.openid_mixin.shouldReauthenticate())

    def test_should_be_False_when_delta_within_range(self):
        """If the last login is within the maximum delta, the user won't have
        to enter their password again.
        """
        self.authdata['logintime'] = datetime.utcnow() - timedelta(seconds=50)
        self.openid_request.args['max_auth_age'] = '3600'
        self.assertEquals(False, self.openid_mixin.shouldReauthenticate())

    def test_should_be_True_when_delta_not_in_range(self):
        """If the last login is not within the maximum delta, they will have
        to enter their password again.
        """
        self.authdata['logintime'] = (
            datetime.utcnow() - timedelta(seconds=3601))
        self.openid_request.args['max_auth_age'] = '3600'
        self.assertEquals(True, self.openid_mixin.shouldReauthenticate())


class OpenIDMixin_checkTeamMembership_TestCase(TestCaseWithFactory):
    """Test cases for the checkTeamMembership() method."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.request = LaunchpadTestRequest(
            SERVER_URL='http://openid.launchpad.net/+openid')
        login("test@canonical.com", self.request)
        self.person = getUtility(IPersonSet).getByEmail(
            'guilherme.salgado@canonical.com')
        self.account = self.factory.makeAccount(
            'Test account, without a person')
        self.account_email = self.factory.makeEmail(
            'test@example.com', None, self.account)
        class CheckTeamMembershipTest(OpenIDMixin):
            # Must create this class so that we can override account, which is
            # a @property on OpenIDMixin.
            account = None
        self.openid_mixin = CheckTeamMembershipTest(None, self.request)
        self.openid_mixin.request = self.request
        self.openid_request = FakeOpenIdRequest()
        self.openid_request.args = {'query_membership': 'admins'}
        self.openid_request.namespace = OPENID2_NS
        self.openid_response = OpenIDResponse(self.openid_request)
        self.openid_mixin.openid_request = self.openid_request

    def tearDown(self):
        logout()

    def test_personless_account(self):
        # A call to checkTeamMembership() won't add anything to the OpenID
        # response if the account has no Person associated with.
        self.openid_mixin.account = self.account
        self.openid_mixin.checkTeamMembership(self.openid_response)
        self.failUnlessEqual(self.openid_response.fields.args, {})

    def test_full_fledged_account(self):
        # A call to checkTeamMembership() will add stuff to the OpenID
        # response if the account has a Person associated with.
        self.openid_mixin.account = self.person.account
        self.openid_mixin.checkTeamMembership(self.openid_response)
        self.failUnlessEqual(
            self.openid_response.fields.args,
            {('http://ns.launchpad.net/2007/openid-teams', 'is_member'):
                'admins'})


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(doctest.DocTestSuite(
        'canonical.launchpad.browser.openidserver'))
    suite.addTest(LayeredDocFileSuite(
        'loginservice.txt',
        'loginservice-dissect-radio-button.txt',
        setUp=setUp, tearDown=tearDown,
        layer=DatabaseFunctionalLayer))
    return suite

if __name__ == '__main__':
    unittest.main()

# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for Login Service related unit tests."""

__metaclass__ = type

__all__ = []

from datetime import datetime, timedelta
import unittest

from openid.message import Message

from zope.component import getUtility
from zope.session.interfaces import ISession
from zope.testing import doctest

from canonical.launchpad.browser.openidserver import OpenIDMixin
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.interfaces import IPersonSet, IOpenIDRPConfigSet
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import DatabaseFunctionalLayer


class SimpleRegistrationTestCase(unittest.TestCase):
    """Tests for Simple Registration helpers in OpenIDMixin"""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)

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
            user = getUtility(IPersonSet).getByEmail('david@canonical.com')
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
            user = person
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


class OpenIDMixin_shouldReauthenticate_TestCase(unittest.TestCase):
    """Test cases for the shouldReauthenticate() period."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Sets up a very simple openid_mixin with a FakeOpenIdRequest.

        The user is set-up to have logged 90 days ago.
        """
        self.request = LaunchpadTestRequest(
            SERVER_URL='http://openid.launchpad.net/+openid')
        login("test@canonical.com", self.request)
        self.openid_mixin = OpenIDMixin(None, self.request)
        self.openid_mixin.user = object()
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


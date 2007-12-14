# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for Login Service related unit tests."""

__metaclass__ = type

__all__ = []

import unittest

from openid.message import Message

from zope.component import getUtility
from zope.testing import doctest

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.browser.openidserver import OpenIdMixin
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)
from canonical.launchpad.interfaces import IPersonSet, IOpenIDRPConfigSet
from canonical.testing import LaunchpadFunctionalLayer


class SimpleRegistrationTestCase(unittest.TestCase):
    """Tests for Simple Registration helpers in OpenIdMixin"""
    layer = LaunchpadFunctionalLayer

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
        class FieldNameTest(OpenIdMixin):
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
        class FieldValueTest(OpenIdMixin):
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
        class FieldValueTest(OpenIdMixin):
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
            ('timezone', u'UTC')])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(doctest.DocTestSuite(
        'canonical.launchpad.browser.openidserver'))
    suite.addTest(FunctionalDocFileSuite(
        'loginservice.txt',
        'loginservice-dissect-radio-button.txt',
        optionflags=default_optionflags, package=__name__,
        setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer))
    return suite

if __name__ == '__main__':
    unittest.main()


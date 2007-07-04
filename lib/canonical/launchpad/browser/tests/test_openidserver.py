# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for Login Service related unit tests."""

__metaclass__ = type

__all__ = []

import unittest

from zope.component import getUtility
from zope.testing import doctest

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.browser.openidserver import (
    KNOWN_TRUST_ROOTS, OpenIdMixin)
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)
from canonical.launchpad.interfaces import IPersonSet
from canonical.testing import LaunchpadFunctionalLayer


class SimpleRegistrationTestCase(unittest.TestCase):
    """Tests for Simple Registration helpers in OpenIdMixin"""
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)
        self.person = getUtility(IPersonSet).getByEmail(
            'david@canonical.com')

    def tearDown(self):
        if 'fake-trust-root' in KNOWN_TRUST_ROOTS:
            del KNOWN_TRUST_ROOTS['fake-trust-root']

    def test_sreg_field_names(self):
        # Test that sreg_field_names returns an appropriate value
        # according to both the OpenID request and the policy defined
        # in KNOWN_TRUST_ROOTS.
        KNOWN_TRUST_ROOTS['fake-trust-root'] = dict(
            title='Fake Trust Root',
            sreg=['email', 'fullname', 'postcode'])
        class FieldNameTest(OpenIdMixin):
            user = self.person
            openid_parameters = {
                'openid.sreg.required': 'email,country,nickname',
                'openid.sreg.optional': 'fullname'}
            class openid_request:
                trust_root = 'fake-trust-root'
        field_name_test = FieldNameTest(None, None)
        # Note that country and nickname are not returned since they
        # are not included in the policy.  Similarly, postcode is not
        # returned since it was not requested.  The field names are
        # returned in a fixed order.
        self.assertEqual(field_name_test.sreg_field_names,
                         ['fullname', 'email'])

    def test_sreg_fields(self):
        # Test that user details are extracted correctly.
        class FieldValueTest(OpenIdMixin):
            user = self.person
            sreg_field_names = [
                'fullname', 'nickname', 'email', 'timezone',
                'x.address1', 'x.address2', 'x.city', 'x.province',
                'country', 'postcode', 'x.phone', 'x.organization']
        field_value_test = FieldValueTest(None, None)
        self.assertEqual(field_value_test.sreg_fields, [
            ('fullname', u'David Allouche'),
            ('nickname', u'ddaa'),
            ('email', u'david.allouche@canonical.com'),
            ('timezone', u'UTC'),
            ('x.address1', u'Velvet Zephyr Woods'),
            ('x.address2', u'5423'),
            ('x.city', u'whatever'),
            ('x.province', u'not mandatory'),
            ('country', u'France'),
            ('postcode', u'999432423'),
            ('x.phone', u'+55 16 3374-2027')])


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


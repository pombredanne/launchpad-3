# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import datetime
import time

from zope.interface import Interface
from zope.component import getUtility
from zope.schema.interfaces import TooShort

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.fields import (
    BlacklistableContentNameField,
    FormattableDate,
    StrippableText,
    )
from lp.registry.interfaces.nameblacklist import INameBlacklistSet
from lp.testing import (
    login_person,
    TestCase,
    TestCaseWithFactory,
    )


def make_target():
    """Make a trivial object to be a target of the field setting."""

    class Simple:
        """A simple class to test setting fields on."""

    return Simple()


class TestFormattableDate(TestCase):

    def test_validation_fails_on_bad_data(self):
        field = FormattableDate()
        date_value = datetime.date(
            *(time.strptime('1000-01-01', '%Y-%m-%d'))[:3])
        self.assertRaises(
            LaunchpadValidationError, field.validate, date_value)

    def test_validation_passes_good_data(self):
        field = FormattableDate()
        date_value = datetime.date(
            *(time.strptime('2010-01-01', '%Y-%m-%d'))[:3])
        self.assertIs(None, field.validate(date_value))


class TestStrippableText(TestCase):

    def test_strips_text(self):
        # The set method should strip the string before setting the field.
        target = make_target()
        field = StrippableText(__name__='test', strip_text=True)
        self.assertTrue(field.strip_text)
        field.set(target, '  testing  ')
        self.assertEqual('testing', target.test)

    def test_default_constructor(self):
        # If strip_text is not set, or set to false, then the text is not
        # stripped when set.
        target = make_target()
        field = StrippableText(__name__='test')
        self.assertFalse(field.strip_text)
        field.set(target, '  testing  ')
        self.assertEqual('  testing  ', target.test)

    def test_setting_with_none(self):
        # The set method is given None, the attribute is set to None
        target = make_target()
        field = StrippableText(__name__='test', strip_text=True)
        field.set(target, None)
        self.assertIs(None, target.test)

    def test_validate_min_contraints(self):
        # The minimum length constraint tests the stripped string.
        field = StrippableText(
            __name__='test', strip_text=True, min_length=1)
        self.assertRaises(TooShort, field.validate, u'  ')

    def test_validate_max_contraints(self):
        # The minimum length constraint tests the stripped string.
        field = StrippableText(
            __name__='test', strip_text=True, max_length=2)
        self.assertEqual(None, field.validate(u'  a  '))


class TestBlacklistableContentNameField(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBlacklistableContentNameField, self).setUp()
        name_blacklist_set = getUtility(INameBlacklistSet)
        self.team = self.factory.makeTeam()
        admin_exp = name_blacklist_set.create(u'fnord', admin=self.team)
        IStore(admin_exp).flush()

    def makeTestField(self):
        """Return testible subclass."""

        class ITestInterface(Interface):
            pass

        class TestField(BlacklistableContentNameField):
            _content_iface = ITestInterface

            def _getByName(self, name):
                return None

        return TestField(__name__='test')

    def test_validate_fails_with_blacklisted_name_anonymous(self):
        # Anonymous users, processes, cannot create a name that matches
        # a blacklisted name.
        field = self.makeTestField()
        date_value = u'fnord'
        self.assertRaises(
            LaunchpadValidationError, field.validate, date_value)

    def test_validate_fails_with_blacklisted_name_not_admin(self):
        # Users who do not adminster a blacklisted name cannot create
        # a matching name.
        field = self.makeTestField()
        date_value = u'fnord'
        login_person(self.factory.makePerson())
        self.assertRaises(
            LaunchpadValidationError, field.validate, date_value)

    def test_validate_passes_for_admin(self):
        # Users in the team that adminsters a blacklisted name may create
        # matching names.
        field = self.makeTestField()
        date_value = u'fnord'
        login_person(self.team.teamowner)
        self.assertEqual(None, field.validate(date_value))

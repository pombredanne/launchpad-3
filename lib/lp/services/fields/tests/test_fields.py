# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from lp.services.fields import StrippableText

from lp.testing import TestCase


class TestStrippableText(TestCase):

    def makeTarget(self):
        """Make a trivial object to be a target of the field setting."""
        class Simple:
            """A simple class to test setting fields on."""
        return Simple()

    def test_strips_text(self):
        # The set method should strip the string before setting the field.
        target = self.makeTarget()
        field = StrippableText(__name__='test', strip_text=True)
        self.assertTrue(field.strip_text)
        field.set(target, '  testing  ')
        self.assertEqual('testing', target.test)

    def test_default_constructor(self):
        # If strip_text is not set, or set to false, then the text is not
        # stripped when set.
        target = self.makeTarget()
        field = StrippableText(__name__='test')
        self.assertFalse(field.strip_text)
        field.set(target, '  testing  ')
        self.assertEqual('  testing  ', target.test)

    def test_setting_with_none(self):
        # The set method is given None, the attribute is set to None
        target = self.makeTarget()
        field = StrippableText(__name__='test', strip_text=True)
        field.set(target, None)
        self.assertIs(None, target.test)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

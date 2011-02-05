# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import datetime
from StringIO import StringIO
import time
import unittest

from canonical.launchpad.validators import LaunchpadValidationError
from lp.services.fields import (
    FormattableDate,
    MugshotImageUpload,
    StrippableText,
    )
from lp.testing import TestCase


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


class TestMugshotImageUpload(TestCase):

    def test_validation_corrupt_image(self):
        # ValueErrors raised by PIL become LaunchpadValidationErrors.
        field = MugshotImageUpload(default_image_resource='dummy')
        image = StringIO(
            '/* XPM */\n'
            'static char *pixmap[] = {\n'
            '"32 32 253 2",\n'
            '  "00 c #01CAA3",\n'
            '  ".. s None c None",\n'
            '};')
        image.filename = 'foo.xpm'
        self.assertRaises(
            LaunchpadValidationError, field.validate, image)

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the session module."""

__metaclass__ = type

import re
import unittest

from datetime import datetime, timedelta

from devscripts.ec2test import session


class TestEC2SessionName(unittest.TestCase):
    """Tests for EC2SessionName."""

    def test_make(self):
        # EC2SessionName.make() is the most convenient way to create
        # valid names.
        name = session.EC2SessionName.make("fred")
        check = re.compile(
            r'^fred/\d{4}-\d{2}-\d{2}-\d{4}/[0-9a-zA-Z]{8}$').match
        self.failIf(check(name) is None, "Did not match %r" % name)
        possible_expires = [
            None, '1986-04-26-0123', timedelta(hours=10),
            datetime(1986, 04, 26, 1, 23)
            ]
        for expires in possible_expires:
            name = session.EC2SessionName.make("fred", expires)
            self.failIf(check(name) is None, "Did not match %r" % name)

    def test_properties(self):
        # A valid EC2SessionName has properies to access the three
        # components of its name.
        base = "fred"
        timestamp = datetime(1986, 4, 26, 1, 23)
        timestamp_string = '1986-04-26-0123'
        rand = 'abcdef123456'
        name = session.EC2SessionName(
            "%s/%s/%s" % (base, timestamp_string, rand))
        self.failUnlessEqual(base, name.base)
        self.failUnlessEqual(timestamp, name.expires)
        self.failUnlessEqual(rand, name.rand)

    def test_invalid_base(self):
        # If the given base contains a forward-slash, an
        # AssertionError should be raised.
        self.failUnlessRaises(
            AssertionError, session.EC2SessionName.make, "forward/slash")

    def test_invalid_timestamp(self):
        # If the given expiry timestamp contains a forward-slash, an
        # AssertionError should be raised.
        self.failUnlessRaises(
            AssertionError, session.EC2SessionName.make, "fred", "/")
        # If the given expiry timestamp does not contain a timestamp
        # in the correct form, an AssertionError should be raised.
        self.failUnlessRaises(
            AssertionError, session.EC2SessionName.make, "fred", "1986.04.26")

    def test_form_not_correct(self):
        # If the form of the string is not base/timestamp/rand then
        # the corresponding properties should all return None.
        broken_name = session.EC2SessionName('bob')
        self.failUnless(broken_name.base is None)
        self.failUnless(broken_name.expires is None)
        self.failUnless(broken_name.rand is None)

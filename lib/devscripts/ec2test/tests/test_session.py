# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the session module."""

__metaclass__ = type

import re
import unittest

from datetime import datetime

from devscripts.ec2test import session


class TestEC2SessionName(unittest.TestCase):
    """Tests for EC2SessionName."""

    def test_make(self):
        name = session.EC2SessionName.make("fred")
        match = re.match(
            r'^fred/\d{4}-\d{2}-\d{2}-\d{4}/[0-9a-zA-Z]{32}$', name)
        self.failIf(match is None, "Did not match %r" % name)

    def test_properties(self):
        base = "fred"
        timestamp = datetime(1986, 4, 26, 1, 23)
        timestamp_string = '1986-04-26-0123'
        rand = 'abcdef123456'
        name = session.EC2SessionName(
            "%s/%s/%s" % (base, timestamp_string, rand))
        self.failUnlessEqual(base, name.base)
        self.failUnlessEqual(timestamp, name.timestamp)
        self.failUnlessEqual(rand, name.rand)

    def test_invalid(self):
        self.failUnlessRaises(
            AssertionError, session.EC2SessionName.make, "forward/slash")
        broken_name = session.EC2SessionName('bob')
        self.failUnless(broken_name.base is None)
        self.failUnless(broken_name.timestamp is None)
        self.failUnless(broken_name.rand is None)

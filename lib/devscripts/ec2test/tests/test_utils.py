# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the utils module."""

__metaclass__ = type

import re
import unittest

from datetime import datetime

from devscripts.ec2test import utils


class TestDateTimeUtils(unittest.TestCase):
    """Tests for date/time related utilities."""

    example_date = datetime(1986, 4, 26, 1, 23)
    example_date_string = '1986-04-26-0123'
    example_date_text = (
        'blah blah foo blah 23545 646 ' +
        example_date_string + ' 435 blah')

    def test_make_datetime_string(self):
        self.failUnlessEqual(
            self.example_date_string,
            utils.make_datetime_string(self.example_date))

    def test_find_datetime_string(self):
        self.failUnlessEqual(
            self.example_date,
            utils.find_datetime_string(self.example_date_string))
        self.failUnlessEqual(
            self.example_date,
            utils.find_datetime_string(self.example_date_text))


class TestRandomUtils(unittest.TestCase):
    """Tests for randomness related utilities."""

    def test_make_random_string(self):
        rand_a = utils.make_random_string()
        rand_b = utils.make_random_string()
        self.failIfEqual(rand_a, rand_b)
        self.failUnlessEqual(32, len(rand_a))
        self.failUnlessEqual(32, len(rand_b))
        hex_chars = set('0123456789abcdefABCDEF')
        self.failUnless(hex_chars.issuperset(rand_a))
        self.failUnless(hex_chars.issuperset(rand_b))

    def test_make_unique_name(self):
        unique_name = utils.make_unique_name("fred")
        match = re.match(
            r'^fred-\d{4}-\d{2}-\d{2}-\d{4}-[0-9a-zA-Z]{32}$', unique_name)
        self.failIf(match is None, "Did not match %r" % unique_name)

    def test_datetime_string_in_unique_name(self):
        unique_name = utils.make_unique_name("fred")
        timestamp = utils.find_datetime_string(unique_name)
        self.failIf(timestamp is None)
        timestamp_string = utils.make_datetime_string(timestamp)
        self.failUnless(timestamp_string in unique_name)

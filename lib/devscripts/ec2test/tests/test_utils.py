# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the utils module."""

__metaclass__ = type

import unittest

from datetime import datetime

from devscripts.ec2test import utils


class TestDateTimeUtils(unittest.TestCase):
    """Tests for the config file parser."""

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

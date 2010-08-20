# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.testing import DatabaseFunctionalLayer

from lp.app.enums import ServiceUsage
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )


class UsageEnumsBaseTestCase(TestCaseWithFactory):
    """Base class for testing the UsageEnums on their pillars."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(UsageEnumsBaseTestCase, self).setUp()
        self.target = None

    def test_answers_usage_no_data(self):
        # By default, we don't know anything about a target
        self.assertEqual(
            ServiceUsage.UNKNOWN,
            self.target.answers_usage)

    def test_answers_usage_using_bool(self):
        # If the old bool says they use Launchpad, return LAUNCHPAD
        # if the ServiceUsage is unknown.
        login_person(self.target.owner)
        self.target.official_answers = True
        self.assertEqual(
            ServiceUsage.LAUNCHPAD,
            self.target.answers_usage)

    def test_answers_usage_with_enum_data(self):
        # If the enum has something other than UNKNOWN as its status,
        # use that.
        login_person(self.target.owner)
        self.target.answers_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            ServiceUsage.EXTERNAL,
            self.target.answers_usage)

    def test_answers_setter(self):
        login_person(self.target.owner)
        self.target.official_answers = True
        self.target.answers_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            False,
            self.target.official_answers)
        self.target.answers_usage = ServiceUsage.LAUNCHPAD
        self.assertEqual(
            True,
            self.target.official_answers)

    def test_codehosting_usage(self):
        # Only test get for codehosting; this has no setter because the
        # state is derived from other data.
        self.assertEqual(
            ServiceUsage.UNKNOWN,
            self.target.codehosting_usage)

    def test_translations_usage_no_data(self):
        # By default, we don't know anything about a target
        self.assertEqual(
            ServiceUsage.UNKNOWN,
            self.target.translations_usage)

    def test_translations_usage_using_bool(self):
        # If the old bool says they use Launchpad, return LAUNCHPAD
        # if the ServiceUsage is unknown.
        login_person(self.target.owner)
        self.target.official_rosetta = True
        self.assertEqual(
            ServiceUsage.LAUNCHPAD,
            self.target.translations_usage)

    def test_translations_usage_with_enum_data(self):
        # If the enum has something other than UNKNOWN as its status,
        # use that.
        login_person(self.target.owner)
        self.target.translations_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            ServiceUsage.EXTERNAL,
            self.target.translations_usage)

    def test_translations_setter(self):
        login_person(self.target.owner)
        self.target.official_rosetta = True
        self.target.translations_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            False,
            self.target.official_rosetta)
        self.target.translations_usage = ServiceUsage.LAUNCHPAD
        self.assertEqual(
            True,
            self.target.official_rosetta)

    def test_bug_tracking_usage(self):
        # Only test get for bug_tracking; this has no setter because the
        # state is derived from other data.
        self.assertEqual(
            ServiceUsage.UNKNOWN,
            self.target.bug_tracking_usage)

    def test_blueprints_usage_no_data(self):
        # By default, we don't know anything about a target
        self.assertEqual(
            ServiceUsage.UNKNOWN,
            self.target.blueprints_usage)

    def test_blueprints_usage_using_bool(self):
        # If the old bool says they use Launchpad, return LAUNCHPAD
        # if the ServiceUsage is unknown.
        login_person(self.target.owner)
        self.target.official_blueprints = True
        self.assertEqual(
            ServiceUsage.LAUNCHPAD,
            self.target.blueprints_usage)

    def test_blueprints_usage_with_enum_data(self):
        # If the enum has something other than UNKNOWN as its status,
        # use that.
        login_person(self.target.owner)
        self.target.blueprints_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            ServiceUsage.EXTERNAL,
            self.target.blueprints_usage)

    def test_blueprints_setter(self):
        login_person(self.target.owner)
        self.target.official_blueprints = True
        self.target.blueprints_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            False,
            self.target.official_blueprints)
        self.target.blueprints_usage = ServiceUsage.LAUNCHPAD
        self.assertEqual(
            True,
            self.target.official_blueprints)


class TestDistributionUsageEnums(UsageEnumsBaseTestCase):
    """Tests the usage enums for the distribution."""

    def setUp(self):
        super(TestDistributionUsageEnums, self).setUp()
        self.target = self.factory.makeDistribution()

    def test_codehosting_usage(self):
        # This method must be changed for Distribution, because its
        # enum defaults to different data.
        self.assertEqual(
            ServiceUsage.NOT_APPLICABLE,
            self.target.codehosting_usage)


class TestProductUsageEnums(UsageEnumsBaseTestCase):
    """Tests the usage enums for the product."""

    def setUp(self):
        super(TestProductUsageEnums, self).setUp()
        self.target = self.factory.makeProduct()

# Manually create the TestLoader list, because the UsageEnumsBaseTestCase
# shouldn't run.
test_list = [
    __name__ + ".TestDistributionUsageEnums",
    __name__ + ".TestProductUsageEnums",
    ]


def test_suite():
    return unittest.TestLoader().loadTestsFromNames(test_list)

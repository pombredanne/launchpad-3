# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for DistributionUpstreamBugReport."""

__metaclass__ = type


import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    logout,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.testing.systemdocs import create_view
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.bugs.browser.distribution_upstream_bug_report import (
    DistributionUpstreamBugReport,
    )


class TestDistributionUpstreamBugReport(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)

    def tearDown(self):
        logout()

    def test_valid_sort_keys_are_valid(self):
        # The valid_sort_keys property of the
        # DistributionUpstreamBugReport view contains a list of the sort
        # keys that the view considers valid. Using any one of these
        # keys, including when prepended with a '-', will lead to it
        # being set as the view's sort_order key.
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        for sort_key in DistributionUpstreamBugReport.valid_sort_keys:
            form = {'sort_by': sort_key}
            view = create_view(ubuntu, '+upstreamreport', form)

            # The sort_order property of DistributionUpstreamBugReport is
            # a tuple in the form (sort_key, reversed).
            view_sort_key, view_sort_reversed = view.sort_order
            self.assertEqual(view_sort_key, sort_key,
                "Expected a sort_key of '%s', got '%s'" %
                (sort_key, view_sort_key))

            # By default, reversed is False.
            self.assertFalse(view_sort_reversed,
                "Sort order should not be reversed for a sort_by value of "
                "%s" % sort_key)

            # Prepending a '-' to sort_by will reverse the sort.
            reversed_key = '-%s' % sort_key
            form = {'sort_by': reversed_key}
            view = create_view(ubuntu, '+upstreamreport', form)

            # The sort_key part of view.sort_order will be the same as
            # for a normal sort.
            view_sort_key, view_sort_reversed = view.sort_order
            self.assertEqual(view_sort_key, sort_key,
                "Expected a sort_key of '%s', got '%s'" %
                (sort_key, view_sort_key))

            # But reversed is now True.
            self.assertTrue(view_sort_reversed,
                "Sort order should be reversed for a sort_by value of "
                "%s" % reversed_key)

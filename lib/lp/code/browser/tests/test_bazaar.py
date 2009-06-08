# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for classes in the lp.code.browser.bazaar module."""

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import DatabaseFunctionalLayer

from lp.code.browser.bazaar import BazaarApplicationView
from lp.testing import ANONYMOUS, login, TestCaseWithFactory


class TestBazaarViewPreCacheLaunchpadPermissions(TestCaseWithFactory):
    """Test the precaching of launchpad.View permissions."""

    layer = DatabaseFunctionalLayer

    def test_precaching_permissions(self):
        # The _precacheViewPermissions method updates the policy cache for
        # launchpad.View.
        branch = self.factory.makeAnyBranch(private=True)
        request = LaunchpadTestRequest()
        login(ANONYMOUS, request)
        view = BazaarApplicationView(object(), request)
        view._precacheViewPermissions([branch])
        self.assertTrue(check_permission('launchpad.View', branch))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


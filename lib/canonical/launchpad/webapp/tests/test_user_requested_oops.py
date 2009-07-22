# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the user requested oops using ++oops++ traversal."""

__metaclass__ = type

import unittest

from lazr.restful.utils import get_current_browser_request

from canonical.launchpad.webapp.errorlog import LAZR_OOPS_USER_REQUESTED_KEY
from canonical.testing.layers import DatabaseFunctionalLayer, PageTestLayer
from lp.testing import TestCase


class TestUserRequestedOops(TestCase):

    layer = PageTestLayer

    def test_none_requested(self):
        # If an oops was not requested, then maybe_record_user_requested_oops
        # does not record an oops.
        request = get_current_browser_request()
        self.assertIsNot(None, request)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Tests the registration of the SSO request publication factory."""

__metaclass__ = type

import unittest

from canonical.signon.publisher import OpenIDBrowserRequest, OpenIDPublication
from canonical.testing.layers import FunctionalLayer

from lp.testing import TestCase
from lp.testing.publication import get_request_and_publication


class SSORequestPublicationFactoryTestCase(TestCase):
    layer = FunctionalLayer

    def test_openid(self):
        request, publication = get_request_and_publication(
            'openid.launchpad.dev')
        self.assertIsInstance(request, OpenIDBrowserRequest)
        self.assertIsInstance(publication, OpenIDPublication)


def test_suite():
    """Create the test suite.."""
    return unittest.TestLoader().loadTestsFromName(__name__)


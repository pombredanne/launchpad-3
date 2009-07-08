# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Tests the registration of ShipIt request publication factories."""

__metaclass__ = type

import unittest

from canonical.shipit.publisher import (
    EdubuntuShipItBrowserRequest, KubuntuShipItBrowserRequest,
    ShipItPublication, UbuntuShipItBrowserRequest)
from canonical.testing.layers import FunctionalLayer

from lp.testing import TestCase
from lp.testing.publication import get_request_and_publication


class ShipItRequestPublicationFactoryTestCase(TestCase):
    layer = FunctionalLayer

    def test_ubuntu_shipit(self):
        request, publication = get_request_and_publication(
            'shipit.ubuntu.dev')
        self.assertIsInstance(request, UbuntuShipItBrowserRequest)
        self.assertIsInstance(publication, ShipItPublication)

    def test_edubuntu_shipit(self):
        request, publication = get_request_and_publication(
            'shipit.edubuntu.dev')
        self.assertIsInstance(request, EdubuntuShipItBrowserRequest)
        self.assertIsInstance(publication, ShipItPublication)

    def test_kubuntu_shipit(self):
        request, publication = get_request_and_publication(
            'shipit.kubuntu.dev')
        self.assertIsInstance(request, KubuntuShipItBrowserRequest)
        self.assertIsInstance(publication, ShipItPublication)


def test_suite():
    """Create the test suite.."""
    return unittest.TestLoader().loadTestsFromName(__name__)


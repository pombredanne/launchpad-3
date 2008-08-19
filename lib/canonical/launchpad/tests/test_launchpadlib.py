# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from launchpadlib.testing.helpers import salgado_with_full_permissions
from canonical.testing import AppServerLayer


class TestLaunchpadLib(unittest.TestCase):
    """Tests for the launchpadlib client for the REST API."""

    layer = AppServerLayer
    launchpad = None

    def setUp(self):
        if self.launchpad is None:
            self.launchpad = salgado_with_full_permissions.login()

    def verifyAttributes(self, element):
        """Verify that launchpadlib can parse the element's attributes."""
        attribute_names = (element.lp_attributes
            + element.lp_entries + element.lp_collections)
        for name in attribute_names:
            getattr(element, name)

    def test_product(self):
        """Test product attributes."""
        self.verifyAttributes(self.launchpad.projects['firefox'])

    def test_person(self):
        """Test person attributes."""
        self.verifyAttributes(self.launchpad.me)

    def test_bug(self):
        """Test bug attributes."""
        self.verifyAttributes(self.launchpad.bugs[1])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

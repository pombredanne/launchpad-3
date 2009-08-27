# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from launchpadlib.testing.helpers import salgado_with_full_permissions
from canonical.testing import AppServerLayer


class TestLaunchpadLib(unittest.TestCase):
    """Tests for the launchpadlib client for the REST API."""

    layer = AppServerLayer
    launchpad = None
    project = None

    def setUp(self):
        if self.launchpad is None:
            self.launchpad = salgado_with_full_permissions.login()
        if self.project is None:
            self.project = self.launchpad.projects['firefox']

    def verifyAttributes(self, element):
        """Verify that launchpadlib can parse the element's attributes."""
        attribute_names = (element.lp_attributes
            + element.lp_entries + element.lp_collections)
        for name in attribute_names:
            getattr(element, name)

    def test_project(self):
        """Test project attributes."""
        self.verifyAttributes(self.project)

    def test_person(self):
        """Test person attributes."""
        self.verifyAttributes(self.launchpad.me)

    def test_bug(self):
        """Test bug attributes."""
        self.verifyAttributes(self.launchpad.bugs[1])

    def test_branch(self):
        """Test branch attributes."""
        branch = self.project.getBranches()[0]
        self.verifyAttributes(branch)

    def test_milestone(self):
        """Test milestone attributes."""
        # launchpadlib can only slice and not subscript
        # so project.milestones[0] doesn't work.
        milestone = self.project.active_milestones[:1][0]
        self.verifyAttributes(milestone)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

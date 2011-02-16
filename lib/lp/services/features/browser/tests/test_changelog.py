# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature flag change log views."""


__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.features.changelog import ChangeLog
from lp.testing import TestCase
from lp.testing.views import create_view


diff = (
    u"-bugs.feature_%(idx)s team:testers 10 on\n"
    u"+bugs.feature_%(idx)s team:testers 10 off")


class TestChangeLogView(TestCase):
    """Test the feature flag ChangeLog view."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestChangeLogView, self).setUp()
        self.root = getUtility(ILaunchpadRoot)
        for i in range(0, 11):
            ChangeLog.append(diff % dict(idx=i))

    def test_batched_page_title(self):
        # The view provides a page_title and label.
        view = create_view(self.root, name='+feature-changelog')
        self.assertEqual(
            view.label, view.page_title)
        self.assertEqual(
            'Feature flag changelog', view.page_title)

    def test_batched_changes(self):
        # The view provides a batched iterator of changes.
        view = create_view(self.root, name='+feature-changelog')
        batch = view.changes
        self.assertEqual('change', batch._singular_heading)
        self.assertEqual('changes', batch._plural_heading)
        self.assertEqual(10, batch.default_size)
        self.assertEqual(2, len(batch.getBatches()))

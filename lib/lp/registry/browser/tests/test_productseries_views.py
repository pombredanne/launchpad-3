# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.config import config
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.testing import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestProductSeriesView(TestCaseWithFactory):
    """Test the product series +index view."""

    layer = LaunchpadZopelessLayer

    def test_milestone_batch_navigator(self):
        product = self.factory.makeProduct()
        for name in ('a', 'b', 'c', 'd'):
            product.development_focus.newMilestone(name)
        view = create_initialized_view(
            product.development_focus, name='+index')
        config.push('default-batch-size', """
        [launchpad]
        default_batch_size: 2
        """)
        self.assert_(
            isinstance(view.milestone_batch_navigator, BatchNavigator),
            'milestone_batch_navigator is not a BatchNavigator object: %r'
            % view.milestone_batch_navigator)
        self.assertEqual(4, view.milestone_batch_navigator.batch.total())
        expected = [
            '0.9.2',
            '0.9.1',
            ]
        milestone_names = [
            item.name
            for item in view.milestone_batch_navigator.currentBatch()]
        config.pop('default-batch-size')

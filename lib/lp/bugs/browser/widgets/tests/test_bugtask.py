# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the bugtask widgets."""

__metaclass__ = type

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.browser.widgets.bugtask import BugTaskTargetWidget
from lp.bugs.interfaces.bugtask import IBugTask
from lp.testing import TestCaseWithFactory


class BugTaskTargetWidgetTestCase(TestCaseWithFactory):
    """Test that BugTaskTargetWidget behaves as expected."""
    layer = DatabaseFunctionalLayer

    def getWidget(self, bugtask):
        field = IBugTask['target']
        bound_field = field.bind(bugtask)
        request = LaunchpadTestRequest()
        return BugTaskTargetWidget(bound_field, request)

    def test_getDistributionVocabulary_with_product_bugtask(self):
        # The vocabulary does not contain distros that do not use
        # launchpad to track bugs.
        distribution = self.factory.makeDistribution()
        product = self.factory.makeProduct()
        bugtask = self.factory.makeBugTask(target=product)
        target_widget = self.getWidget(bugtask)
        vocabulary = target_widget.getDistributionVocabulary()
        self.assertEqual(None, vocabulary.distribution)
        self.assertFalse(
            distribution in vocabulary,
            "Vocabulary contains distros that do not use Launchpad Bugs.")

    def test_getDistributionVocabulary_with_distribution_bugtask(self):
        # The vocabulary does not contain distros that do not use
        # launchpad to track bugs.
        distribution = self.factory.makeDistribution()
        other_distribution = self.factory.makeDistribution()
        bugtask = self.factory.makeBugTask(target=distribution)
        target_widget = self.getWidget(bugtask)
        vocabulary = target_widget.getDistributionVocabulary()
        self.assertEqual(distribution, vocabulary.distribution)
        self.assertTrue(
            distribution in vocabulary,
            "Vocabulary missing context distribution.")
        self.assertFalse(
            other_distribution in vocabulary,
            "Vocabulary contains distros that do not use Launchpad Bugs.")

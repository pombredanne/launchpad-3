# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the bug domain vocabularies."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.vocabulary import UsesBugsDistributionVocabulary
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class UsesBugsDistributionVocabularyTestCase(TestCaseWithFactory):
    """Test that the vocabulary behaves as expected."""
    layer = DatabaseFunctionalLayer

    def test_init_with_distribution(self):
        # When the context is adaptable to IDistribution, it also provides
        # the distribution.
        distribution = self.factory.makeDistribution()
        vocabulary = UsesBugsDistributionVocabulary(distribution)
        self.assertEqual(distribution, vocabulary.context)

    def test_contains_distros_that_use_bugs(self):
        # The vocabulary contains distributions that also use
        # Launchpad to track bugs.
        distro_less_bugs = self.factory.makeDistribution()
        distro_uses_bugs = self.factory.makeDistribution()
        with person_logged_in(distro_uses_bugs.owner):
            distro_uses_bugs.official_malone = True
        vocabulary = UsesBugsDistributionVocabulary()
        self.assertFalse(
            distro_less_bugs in vocabulary,
            "Vocabulary contains distros that do not use Launchpad Bugs.")
        self.assertTrue(
            distro_uses_bugs in vocabulary,
            "Vocabulary missing distros that use Launchpad Bugs.")

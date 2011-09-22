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
        # When the context is adaptable to IDistribution, the distribution
        # property is the distribution.
        distribution = self.factory.makeDistribution()
        vocabulary = UsesBugsDistributionVocabulary(distribution)
        self.assertEqual(distribution, vocabulary.context)
        self.assertEqual(distribution, vocabulary.distribution)

    def test_init_without_distribution(self):
        # When the context is not adaptable to IDistribution, the
        # distribution property is None
        thing = self.factory.makeProduct()
        vocabulary = UsesBugsDistributionVocabulary(thing)
        self.assertEqual(thing, vocabulary.context)
        self.assertEqual(None, vocabulary.distribution)

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

    def test_contains_context_distro(self):
        # The vocabulary contains the context distro even it it does not
        # use Launchpad to track bugs. The distro may have tracked bugs
        # in the past so it is a legitimate choise for historic data.
        distro_less_bugs = self.factory.makeDistribution()
        vocabulary = UsesBugsDistributionVocabulary(distro_less_bugs)
        self.assertFalse(distro_less_bugs.official_malone)
        self.assertTrue(
            distro_less_bugs in vocabulary,
            "Vocabulary missing context distro.")

    def test_contains_missing_context(self):
        # The vocabulary contains the context distro even it it does not
        # use Launchpad to track bugs. The distro may have tracked bugs
        # in the past so it is a legitimate choise for historic data.
        thing = self.factory.makeProduct()
        vocabulary = UsesBugsDistributionVocabulary(thing)
        self.assertFalse(
            thing in vocabulary,
            "Vocabulary contains a non-distribution.")

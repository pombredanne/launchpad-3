# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the answers domain vocabularies."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.answers.vocabulary import UsesAnswersDistributionVocabulary
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class UsesAnswersDistributionVocabularyTestCase(TestCaseWithFactory):
    """Test that the vocabulary behaves as expected."""
    layer = DatabaseFunctionalLayer

    def test_init_with_distribution(self):
        # When the context is adaptable to IDistribution, the distribution
        # property is the distribution.
        distribution = self.factory.makeDistribution()
        vocabulary = UsesAnswersDistributionVocabulary(distribution)
        self.assertEqual(distribution, vocabulary.context)
        self.assertEqual(distribution, vocabulary.distribution)

    def test_init_without_distribution(self):
        # When the context is not adaptable to IDistribution, the
        # distribution property is None
        thing = self.factory.makeProduct()
        vocabulary = UsesAnswersDistributionVocabulary(thing)
        self.assertEqual(thing, vocabulary.context)
        self.assertEqual(None, vocabulary.distribution)

    def test_contains_distros_that_use_answers(self):
        # The vocabulary contains distributions that also use
        # Launchpad to track answers.
        distro_less_answers = self.factory.makeDistribution()
        distro_uses_answers = self.factory.makeDistribution()
        with person_logged_in(distro_uses_answers.owner):
            distro_uses_answers.official_answers = True
        vocabulary = UsesAnswersDistributionVocabulary()
        self.assertFalse(
            distro_less_answers in vocabulary,
            "Vocabulary contains distros that do not use Launchpad Answers.")
        self.assertTrue(
            distro_uses_answers in vocabulary,
            "Vocabulary missing distros that use Launchpad Answers.")

    def test_contains_context_distro(self):
        # The vocabulary contains the context distro even it it does not
        # use Launchpad to track answers. The distro may have tracked answers
        # in the past so it is a legitimate choise for historic data.
        distro_less_answers = self.factory.makeDistribution()
        vocabulary = UsesAnswersDistributionVocabulary(distro_less_answers)
        self.assertFalse(distro_less_answers.official_answers)
        self.assertTrue(
            distro_less_answers in vocabulary,
            "Vocabulary missing context distro.")

    def test_contains_missing_context(self):
        # The vocabulary contains does not contain the context if the
        # context is not adaptable to a distribution.
        thing = self.factory.makeProduct()
        vocabulary = UsesAnswersDistributionVocabulary(thing)
        self.assertFalse(
            thing in vocabulary,
            "Vocabulary contains a non-distribution.")

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the bug domain vocabularies."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.vocabulary import UsesBugsDistributionVocabulary
from lp.testing import TestCaseWithFactory


class UsesBugsDistributionVocabularyTestCase(TestCaseWithFactory):
    """Test that the vocabulary behaves as expected."""
    layer = DatabaseFunctionalLayer

    def test_init_with_distribution(self):
        # When the context is adaptable to IDistribution, it also provides
        # the distribution.
        distribution = self.factory.makeDistribution()
        vocabulary = UsesBugsDistributionVocabulary(distribution)
        self.assertEqual(distribution, vocabulary.context)

# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Distribution Source Package vocabulary."""

__metaclass__ = type


from testtools.matchers import MatchesStructure

from lp.registry.enums import (
    InformationType,
    PRIVATE_INFORMATION_TYPES,
    PUBLIC_INFORMATION_TYPES,
    )
from lp.registry.vocabularies import InformationTypeVocabulary
from lp.services.features.testing import FeatureFixture
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestInformationTypeVocabulary(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_vocabulary_items(self):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        vocab = InformationTypeVocabulary(product)
        for info_type in InformationType:
            self.assertIn(info_type.value, vocab)

    def test_vocabulary_items_project(self):
        # The vocab has all info types for a project without private_bugs set.
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        vocab = InformationTypeVocabulary(product)
        for info_type in InformationType:
            self.assertIn(info_type.value, vocab)

    def test_vocabulary_items_private_bugs_project(self):
        # The vocab has private info types for a project with private_bugs set.
        product = self.factory.makeProduct(private_bugs=True)
        self.factory.makeCommercialSubscription(product)
        vocab = InformationTypeVocabulary(product)
        for info_type in PRIVATE_INFORMATION_TYPES:
            self.assertIn(info_type, vocab)
        for info_type in PUBLIC_INFORMATION_TYPES:
            self.assertNotIn(info_type, vocab)

    def test_getTermByToken(self):
        vocab = InformationTypeVocabulary()
        self.assertThat(
            vocab.getTermByToken('PUBLIC'),
            MatchesStructure.byEquality(
                value=InformationType.PUBLIC,
                token='PUBLIC',
                title='Public',
                description=InformationType.PUBLIC.description))

    def test_proprietary_disabled(self):
        feature_flag = {
            'disclosure.proprietary_information_type.disabled': 'on'}
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        with FeatureFixture(feature_flag):
            vocab = InformationTypeVocabulary(product)
            self.assertRaises(
                LookupError, vocab.getTermByToken, 'PROPRIETARY')

    def test_proprietary_disabled_for_non_commercial_projects(self):
        # Only projects with commercial subscriptions have PROPRIETARY.
        product = self.factory.makeProduct()
        vocab = InformationTypeVocabulary(product)
        self.assertRaises(
            LookupError, vocab.getTermByToken, 'PROPRIETARY')

    def test_proprietary_enabled(self):
        # Only projects with commercial subscriptions have PROPRIETARY.
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        vocab = InformationTypeVocabulary(product)
        term = vocab.getTermByToken('PROPRIETARY')
        self.assertEqual('Proprietary', term.title)

    def test_display_userdata_as_private(self):
        feature_flag = {
            'disclosure.display_userdata_as_private.enabled': 'on'}
        with FeatureFixture(feature_flag):
            vocab = InformationTypeVocabulary()
            term = vocab.getTermByToken('USERDATA')
            self.assertEqual('Private', term.title)
            self.assertTextMatchesExpressionIgnoreWhitespace(
                "Visible only to users with whom the project has "
                "shared private information.",
                term.description)

    def test_userdata(self):
        vocab = InformationTypeVocabulary()
        term = vocab.getTermByToken('USERDATA')
        self.assertEqual('User Data', term.title)
        self.assertTextMatchesExpressionIgnoreWhitespace(
            "Visible only to users with whom the project has shared "
            "information containing user data.",
            term.description)

    def test_multi_pillar_bugs(self):
        # Multi-pillar bugs are forbidden from being PROPRIETARY, no matter
        # the setting of proprietary_information_type.disabled.
        bug = self.factory.makeBug()
        self.factory.makeBugTask(bug=bug, target=self.factory.makeProduct())
        vocab = InformationTypeVocabulary(bug)
        self.assertRaises(LookupError, vocab.getTermByToken, 'PROPRIETARY')

    def test_multi_task_bugs(self):
        # Multi-task bugs are allowed to be PROPRIETARY.
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        bug = self.factory.makeBug(product=product)
        self.factory.makeBugTask(bug=bug) # Uses the same pillar.
        vocab = InformationTypeVocabulary(bug)
        term = vocab.getTermByToken('PROPRIETARY')
        self.assertEqual('Proprietary', term.title)

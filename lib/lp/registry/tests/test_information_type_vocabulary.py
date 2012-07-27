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
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
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

    def test_vocabulary_items_custom(self):
        # The vocab can be given a custom set of types to include.
        vocab = InformationTypeVocabulary(
            types=[InformationType.PUBLICSECURITY, InformationType.USERDATA])
        self.assertIn(InformationType.USERDATA, vocab)
        self.assertNotIn(InformationType.PUBLIC, vocab)

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
        # The feature flag disables proprietary even if it would otherwise be
        # included.
        feature_flag = {
            'disclosure.proprietary_information_type.disabled': 'on'}
        with FeatureFixture(feature_flag):
            product = self.factory.makeProduct()
            vocab = InformationTypeVocabulary(product)
            self.assertRaises(
                LookupError, vocab.getTermByToken, 'PROPRIETARY')

    def test_proprietary_disabled_for_non_commercial_projects(self):
        # Only projects with commercial subscriptions have PROPRIETARY.
        product = self.factory.makeProduct()
        vocab = InformationTypeVocabulary(product)
        self.assertRaises(
            LookupError, vocab.getTermByToken, 'PROPRIETARY')

    def test_proprietary_enabled_for_commercial_projects(self):
        # Only projects with commercial subscriptions have PROPRIETARY.
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        vocab = InformationTypeVocabulary(product)
        term = vocab.getTermByToken('PROPRIETARY')
        self.assertEqual('Proprietary', term.title)

    def test_proprietary_enabled_for_contexts_already_proprietary(self):
        # The vocabulary has PROPRIETARY for contexts which are already
        # proprietary.
        owner = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.PROPRIETARY)
        with person_logged_in(owner):
            vocab = InformationTypeVocabulary(bug)
        term = vocab.getTermByToken('PROPRIETARY')
        self.assertEqual('Proprietary', term.title)

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

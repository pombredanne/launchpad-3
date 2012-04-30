# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Distribution Source Package vocabulary."""

__metaclass__ = type


from testtools.matchers import MatchesStructure

from lp.registry.enums import InformationType
from lp.registry.vocabularies import InformationTypeVocabulary
from lp.services.features.testing import FeatureFixture
from lp.testing import TestCase
from lp.testing.layers import DatabaseFunctionalLayer


class TestInformationTypeVocabulary(TestCase):

    layer = DatabaseFunctionalLayer

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
        with FeatureFixture(feature_flag):
            vocab = InformationTypeVocabulary()
            self.assertRaises(
                LookupError, vocab.getTermByToken, 'PROPRIETARY')

    def test_proprietary_enabled(self):
        vocab = InformationTypeVocabulary()
        term = vocab.getTermByToken('PROPRIETARY')
        self.assertEqual('Proprietary', term.title)

    def test_display_userdata_as_private(self):
        feature_flag = {
            'disclosure.display_userdata_as_private.enabled': 'on'}
        with FeatureFixture(feature_flag):
            vocab = InformationTypeVocabulary()
            term = vocab.getTermByToken('USERDATA')
            self.assertEqual('Private', term.title)
            self.assertEqual(
                "Only users with permission to see the project's artifacts "
                "containing\nprivate information can see this "
                "information.\n",
                term.description)

    def test_userdata(self):
        vocab = InformationTypeVocabulary()
        term = vocab.getTermByToken('USERDATA')
        self.assertEqual('User Data', term.title)
        self.assertEqual(
            "Only users with permission to see the project's artifacts "
            "containing\nuser data can see this information.\n",
            term.description)

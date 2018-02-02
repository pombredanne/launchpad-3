# Copyright 2012-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Soyuz vocabularies."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testtools.matchers import MatchesStructure

from lp.soyuz.vocabularies import PPAVocabulary
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestPPAVocabulary(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_toTerm_empty_description(self):
        archive = self.factory.makeArchive(description='')
        vocab = PPAVocabulary()
        term = vocab.toTerm(archive)
        self.assertThat(term, MatchesStructure.byEquality(
            value=archive,
            token=archive.reference,
            title='No description available'))

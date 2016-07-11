# Copyright 2010-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the source package name vocabularies."""

__metaclass__ = type

from testtools.matchers import (
    Matcher,
    MatchesListwise,
    MatchesSetwise,
    MatchesStructure,
    )
from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.registry.vocabularies import SourcePackageNameVocabulary
from lp.soyuz.enums import ArchivePurpose
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class MatchesSourcePackageNameTerms(Matcher):

    def __init__(self, names, ordered=True):
        self.names = names
        self.ordered = ordered

    def match(self, terms):
        matchers = [
            MatchesStructure.byEquality(
                title=name, token=name,
                value=getUtility(ISourcePackageNameSet)[name])
            for name in self.names]
        if self.ordered:
            return MatchesListwise(matchers).match(terms)
        else:
            return MatchesSetwise(*matchers).match(terms)


class TestSourcePackageNameVocabulary(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSourcePackageNameVocabulary, self).setUp()
        self.vocabulary = SourcePackageNameVocabulary()
        self.spns = [
            self.factory.makeSourcePackageName(name=name)
            for name in (
                'bedbugs', 'bedbugs-aggressive', 'beetles',
                'moths', 'moths-secret')]
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        distroseries = self.factory.makeDistroSeries(distribution=ubuntu)
        for archive in list(ubuntu.all_distro_archives):
            for spn in self.spns[:3]:
                self.factory.makeDSPCache(
                    distroseries=distroseries, sourcepackagename=spn,
                    archive=archive)
        ppa = self.factory.makeArchive(
            distribution=ubuntu, purpose=ArchivePurpose.PPA)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename=self.spns[3],
            archive=ppa)
        private_ppa = self.factory.makeArchive(
            distribution=ubuntu, purpose=ArchivePurpose.PPA, private=True)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename=self.spns[4],
            archive=private_ppa)

    def test_searchForTerms(self):
        # searchForTerms returns appropriate source package names.
        self.assertThat(
            self.vocabulary.searchForTerms('bedbugs'),
            MatchesSourcePackageNameTerms(['bedbugs', 'bedbugs-aggressive']))
        self.assertThat(
            self.vocabulary.searchForTerms('bedbugs-aggressive'),
            MatchesSourcePackageNameTerms(['bedbugs-aggressive']))
        self.assertThat(
            self.vocabulary.searchForTerms('be'),
            MatchesSourcePackageNameTerms(
                ['bedbugs', 'bedbugs-aggressive', 'beetles'], ordered=False))

    def test_searchForTerms_ignores_private_archives(self):
        # searchForTerms only returns results from public archives, unless
        # there is an exact match.
        self.assertThat(
            self.vocabulary.searchForTerms('moths'),
            MatchesSourcePackageNameTerms(['moths']))
        self.assertThat(
            self.vocabulary.searchForTerms('moths-secret'),
            MatchesSourcePackageNameTerms(['moths-secret']))

    def test_toTerm(self):
        # Source package name terms are composed of name, and the spn.
        term = self.vocabulary.toTerm(self.spns[0])
        self.assertEqual(self.spns[0].name, term.title)
        self.assertEqual(self.spns[0].name, term.token)
        self.assertEqual(self.spns[0], term.value)

    def test_getTermByToken(self):
        # Tokens are case-insensitive because the name is lowercase.
        term = self.vocabulary.getTermByToken('BedBUGs')
        self.assertEqual(self.spns[0], term.value)

    def test_getTermByToken_LookupError(self):
        # getTermByToken() raises a LookupError when no match is found.
        self.assertRaises(
            LookupError,
            self.vocabulary.getTermByToken, 'does-notexist')

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Distribution Source Package vocabulary."""

__metaclass__ = type

import transaction

from zope.component import getUtility

from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    reconnect_stores,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.vocabularies import DistributionSourcePackageVocabulary
from lp.soyuz.model.distributionsourcepackagecache import (
    DistributionSourcePackageCache,
    )
from lp.testing import TestCaseWithFactory


class TestDistributionSourcePackageVocabulary(TestCaseWithFactory):
    """Test that the vocabulary behaves as expected."""
    layer = DatabaseFunctionalLayer

    def test_provides_ihugevocabulary(self):
        vocabulary = DistributionSourcePackageVocabulary(
            self.factory.makeDistribution())
        self.assertProvides(vocabulary, IHugeVocabulary)

    def test_init_IDistribution(self):
        # When the context is adaptable to IDistribution, it also provides
        # the distribution.
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        vocabulary = DistributionSourcePackageVocabulary(dsp)
        self.assertEqual(dsp, vocabulary.context)
        self.assertEqual(dsp.distribution, vocabulary.distribution)
        self.assertEqual(dsp, vocabulary.dsp)

    def test_init_dsp_bugtask(self):
        # A dsp bugtask can be the context
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        bugtask = self.factory.makeBugTask(target=dsp)
        vocabulary = DistributionSourcePackageVocabulary(bugtask)
        self.assertEqual(bugtask, vocabulary.context)
        self.assertEqual(dsp.distribution, vocabulary.distribution)
        self.assertEqual(dsp, vocabulary.dsp)

    def test_init_dsp_question(self):
        # A dsp bugtask can be the context
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        question = self.factory.makeQuestion(
            target=dsp, owner=dsp.distribution.owner)
        vocabulary = DistributionSourcePackageVocabulary(question)
        self.assertEqual(question, vocabulary.context)
        self.assertEqual(dsp.distribution, vocabulary.distribution)
        self.assertEqual(dsp, vocabulary.dsp)

    def test_init_no_distribution(self):
        # The distribution is None if the context cannot be adapted to a
        # distribution.
        project = self.factory.makeProduct()
        vocabulary = DistributionSourcePackageVocabulary(project)
        self.assertEqual(project, vocabulary.context)
        self.assertEqual(None, vocabulary.distribution)
        self.assertEqual(None, vocabulary.dsp)

    def test_getDistributionAndPackageName_distro_and_package(self):
        # getDistributionAndPackageName() returns a tuple of distribution
        # and package name when the text contains both.
        new_distro = self.factory.makeDistribution(name='fnord')
        vocabulary = DistributionSourcePackageVocabulary(None)
        distribution, package_name = vocabulary.getDistributionAndPackageName(
            'fnord/pting')
        self.assertEqual(new_distro, distribution)
        self.assertEqual('pting', package_name)

    def test_getDistributionAndPackageName_default_distro_and_package(self):
        # getDistributionAndPackageName() returns a tuple of the default
        # distribution and package name when the text is just a package name.
        default_distro = self.factory.makeDistribution(name='fnord')
        vocabulary = DistributionSourcePackageVocabulary(default_distro)
        distribution, package_name = vocabulary.getDistributionAndPackageName(
            'pting')
        self.assertEqual(default_distro, distribution)
        self.assertEqual('pting', package_name)

    def test_getDistributionAndPackageName_bad_distro_and_package(self):
        # getDistributionAndPackageName() returns a tuple of the default
        # distribution and package name when the distro in the text cannot
        # be matched to a real distro.
        default_distro = self.factory.makeDistribution(name='fnord')
        vocabulary = DistributionSourcePackageVocabulary(default_distro)
        distribution, package_name = vocabulary.getDistributionAndPackageName(
            'misspelled/pting')
        self.assertEqual(default_distro, distribution)
        self.assertEqual('pting', package_name)

    def test_contains_true_without_init(self):
        # The vocabulary contains official DSPs.
        dsp = self.factory.makeDistributionSourcePackage(with_db=True)
        vocabulary = DistributionSourcePackageVocabulary(None)
        self.assertTrue(dsp in vocabulary)

    def test_contains_true_with_init(self):
        # The vocabulary does contain the DSP passed to init when
        # it is not official.
        dsp = self.factory.makeDistributionSourcePackage(with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(dsp)
        self.assertTrue(dsp in vocabulary)

    def test_contains_false_without_init(self):
        # The vocabulary does not contain DSPs that are not official
        # that were not passed to init.
        dsp = self.factory.makeDistributionSourcePackage(with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(None)
        self.assertFalse(dsp in vocabulary)

    def test_toTerm_raises_error(self):
        # An error is raised for DSP/SPNs that are not official and are
        # not in the vocabulary.
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        self.assertRaises(LookupError, vocabulary.toTerm, dsp.name)

    def test_toTerm_none_raises_error(self):
        # An error is raised for SPN does not exist.
        vocabulary = DistributionSourcePackageVocabulary(None)
        self.assertRaises(LookupError, vocabulary.toTerm, 'non-existant')

    def test_toTerm_spn_and_default_distribution(self):
        # The vocabulary's distribution is used when only a SPN is passed.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.sourcepackagerelease.distrosourcepackage
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        term = vocabulary.toTerm(dsp.sourcepackagename)
        expected_token = '%s/%s' % (dsp.distribution.name, dsp.name)
        self.assertEqual(expected_token, term.token)
        self.assertEqual(dsp, term.value)

    def test_toTerm_spn_and_distribution(self):
        # The distribution is used with the spn if it is passed.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.sourcepackagerelease.distrosourcepackage
        vocabulary = DistributionSourcePackageVocabulary(None)
        term = vocabulary.toTerm(dsp.sourcepackagename, dsp.distribution)
        expected_token = '%s/%s' % (dsp.distribution.name, dsp.name)
        self.assertEqual(expected_token, term.token)
        self.assertEqual(dsp, term.value)

    def test_toTerm_dsp(self):
        # The DSP's distribution is used when a DSP is passed.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.sourcepackagerelease.distrosourcepackage
        vocabulary = DistributionSourcePackageVocabulary(dsp)
        term = vocabulary.toTerm(dsp)
        expected_token = '%s/%s' % (dsp.distribution.name, dsp.name)
        self.assertEqual(expected_token, term.token)
        self.assertEqual(dsp, term.value)

    def test_getTermByToken_error(self):
        # An error is raised if the token does not match a official DSP.
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        token = '%s/%s' % (dsp.distribution.name, dsp.name)
        self.assertRaises(LookupError, vocabulary.getTermByToken, token)

    def test_getTermByToken_token(self):
        # The term is return if it matches an official DSP.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.sourcepackagerelease.distrosourcepackage
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        token = '%s/%s' % (dsp.distribution.name, dsp.name)
        term = vocabulary.getTermByToken(token)
        self.assertEqual(dsp, term.value)

    def test_searchForTerms_without_distribution(self):
        # An empty result set is return if the vocabulary has no distribution
        # and the search does not provide distribution information.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.sourcepackagerelease.distrosourcepackage
        vocabulary = DistributionSourcePackageVocabulary(dsp.name)
        results = vocabulary.searchForTerms(dsp.name)
        self.assertIs(0, results.count())

    def makeDSPCache(self, distro_name, package_name, make_distro=True,
                     official=True, binary_names=None, archive=None):
        if make_distro:
            distribution = self.factory.makeDistribution(name=distro_name)
        else:
            distribution = getUtility(IDistributionSet).getByName(distro_name)
        dsp = self.factory.makeDistributionSourcePackage(
            distribution=distribution, sourcepackagename=package_name,
            with_db=official)
        if archive is None:
            archive = dsp.distribution.main_archive
        transaction.commit()
        reconnect_stores('statistician')
        DistributionSourcePackageCache(
            distribution=dsp.distribution,
            sourcepackagename=dsp.sourcepackagename,
            archive=archive,
            name=package_name,
            binpkgnames=binary_names)
        transaction.commit()
        reconnect_stores('launchpad')

    def test_searchForTerms_None(self):
        # Searching for nothing gets you that.
        vocabulary = DistributionSourcePackageVocabulary(
            self.factory.makeDistribution())
        results = vocabulary.searchForTerms()
        self.assertIs(0, results.count())

    def test_searchForTerms_exact_offcial_source_name(self):
        # Exact binary name matches are found.
        self.makeDSPCache('fnord', 'snarf')
        vocabulary = DistributionSourcePackageVocabulary(None)
        results = vocabulary.searchForTerms(query='fnord/snarf')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('fnord/snarf', terms[0].token)

    def test_searchForTerms_similar_offcial_source_name(self):
        # Partial source name matches are found.
        self.makeDSPCache('fnord', 'pting-snarf-ack')
        vocabulary = DistributionSourcePackageVocabulary(None)
        results = vocabulary.searchForTerms(query='fnord/snarf')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('fnord/pting-snarf-ack', terms[0].token)

    def test_searchForTerms_exact_binary_name(self):
        # Exact binary name matches are found.
        self.makeDSPCache(
            'fnord', 'snarf', binary_names='pting-dev pting ack')
        vocabulary = DistributionSourcePackageVocabulary(None)
        results = vocabulary.searchForTerms(query='fnord/pting')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('fnord/snarf', terms[0].token)

    def test_searchForTerms_similar_binary_name(self):
        # Partial binary name matches are found.
        self.makeDSPCache(
            'fnord', 'snarf', binary_names='thrpp pting-dev ack')
        vocabulary = DistributionSourcePackageVocabulary(None)
        results = vocabulary.searchForTerms(query='fnord/pting')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('fnord/snarf', terms[0].token)

    def test_searchForTerms_exact_unofficial_source_name(self):
        # Unofficial source packages are not found by search.
        self.makeDSPCache('fnord', 'snarf', official=False)
        vocabulary = DistributionSourcePackageVocabulary(None)
        results = vocabulary.searchForTerms(query='fnord/snarf')
        terms = list(results)
        self.assertEqual(0, len(terms))

    def test_searchForTerms_similar_unofficial_binary_name(self):
        # Unofficial binary packages are not found by search.
        self.makeDSPCache(
            'fnord', 'snarf', official=False, binary_names='thrpp pting ack')
        vocabulary = DistributionSourcePackageVocabulary(None)
        results = vocabulary.searchForTerms(query='fnord/pting')
        terms = list(results)
        self.assertEqual(0, len(terms))

    def test_searchForTerms_match_official_source_package_branch(self):
        # The official package that is only a branch can be matched
        # by source name if it was built in another distro.
        self.makeDSPCache('fnord', 'snarf')
        distribution = self.factory.makeDistribution(name='pting')
        self.factory.makeDistributionSourcePackage(
            distribution=distribution, sourcepackagename='snarf',
            with_db=True)
        vocabulary = DistributionSourcePackageVocabulary(None)
        results = vocabulary.searchForTerms(query='pting/snarf')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('pting/snarf', terms[0].token)

    def test_searchForTerms_match_official_binary_package_branch(self):
        # The official package that is only a branch can be matched
        # by binary name if it was built in another distro.
        self.makeDSPCache(
            'fnord', 'snarf', binary_names='thrpp snarf-dev ack')
        distribution = self.factory.makeDistribution(name='pting')
        self.factory.makeDistributionSourcePackage(
            distribution=distribution, sourcepackagename='snarf',
            with_db=True)
        vocabulary = DistributionSourcePackageVocabulary(None)
        results = vocabulary.searchForTerms(query='pting/ack')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('pting/snarf', terms[0].token)

    def test_searchForTerms_ranking(self):
        # Exact matches are ranked higher than similar matches.
        self.makeDSPCache('fnord', 'snarf')
        self.makeDSPCache('fnord', 'snarf-server', make_distro=False)
        self.makeDSPCache(
            'fnord', 'pting-devel', binary_names='snarf', make_distro=False)
        self.makeDSPCache(
            'fnord', 'pting-client', binary_names='snarf-common',
            make_distro=False)
        vocabulary = DistributionSourcePackageVocabulary(None)
        results = vocabulary.searchForTerms(query='fnord/snarf')
        terms = list(results)
        self.assertEqual(4, len(terms))
        self.assertEqual('fnord/snarf', terms[0].token)
        self.assertEqual('fnord/pting-devel', terms[1].token)
        self.assertEqual('fnord/snarf-server', terms[2].token)
        self.assertEqual('fnord/pting-client', terms[3].token)

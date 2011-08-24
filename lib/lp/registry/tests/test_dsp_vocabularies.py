# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Distribution Source Package vocabulary."""

__metaclass__ = type

from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.vocabularies import DistributionSourcePackageVocabulary
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

    def test_init_dsp_bugtask(self):
        # A dsp bugtask can be the context
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        bugtask = self.factory.makeBugTask(target=dsp)
        vocabulary = DistributionSourcePackageVocabulary(bugtask)
        self.assertEqual(bugtask, vocabulary.context)
        self.assertEqual(dsp.distribution, vocabulary.distribution)

    def test_init_dsp_question(self):
        # A dsp bugtask can be the context
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        question = self.factory.makeQuestion(
            target=dsp, owner=dsp.distribution.owner)
        vocabulary = DistributionSourcePackageVocabulary(question)
        self.assertEqual(question, vocabulary.context)
        self.assertEqual(dsp.distribution, vocabulary.distribution)

    def test_init_no_distribution(self):
        # The distribution is None if the context cannot be adapted to a
        # distribution.
        project = self.factory.makeProduct()
        vocabulary = DistributionSourcePackageVocabulary(project)
        self.assertEqual(project, vocabulary.context)
        self.assertEqual(None, vocabulary.distribution)

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

    def test_contains_true(self):
        # The vocabulary contains DSPs that have SPPH in the distro.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.sourcepackagerelease.distrosourcepackage
        vocabulary = DistributionSourcePackageVocabulary(dsp)
        self.assertTrue(dsp in vocabulary)

    def test_contains_false(self):
        # The vocabulary does not contain DSPs without SPPH.
        spn = self.factory.makeSourcePackageName(name='foo')
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename=spn)
        vocabulary = DistributionSourcePackageVocabulary(dsp)
        self.assertFalse(dsp in vocabulary)

    def test_toTerm_raises_error(self):
        # An error is raised for DSP/SPNs without publishing history.
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
        # An error is raised if the token does not match a published DSP.
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        token = '%s/%s' % (dsp.distribution.name, dsp.name)
        self.assertRaises(LookupError, vocabulary.getTermByToken, token)

    def test_getTermByToken_token(self):
        # The term is return if it matches a published DSP.
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

    def test_searchForTerms_None(self):
        # Searching for nothing gets you that.
        vocabulary = DistributionSourcePackageVocabulary(
            self.factory.makeDistribution())
        results = vocabulary.searchForTerms()
        self.assertIs(0, results.count())

    def assertTermsEqual(self, expected, actual):
        # Assert two given terms are equal.
        self.assertEqual(expected.token, actual.token)
        self.assertEqual(expected.title, actual.title)
        self.assertEqual(expected.value, actual.value)

    def test_searchForTerms_published_source(self):
        # When we search for a source package name that is published, it is
        # returned.
        spph = self.factory.makeSourcePackagePublishingHistory()
        vocabulary = DistributionSourcePackageVocabulary(
            context=spph.distroseries.distribution)
        results = vocabulary.searchForTerms(query=spph.source_package_name)
        self.assertTermsEqual(
            vocabulary.toTerm(spph.source_package_name), list(results)[0])

    def test_searchForTerms_unpublished_source(self):
        # If the source package name isn't published in the distribution,
        # we get no results.
        spph = self.factory.makeSourcePackagePublishingHistory()
        vocabulary = DistributionSourcePackageVocabulary(
            context=self.factory.makeDistribution())
        results = vocabulary.searchForTerms(query=spph.source_package_name)
        self.assertEqual([], list(results))

    def test_searchForTerms_unpublished_binary(self):
        # If the binary package name isn't published in the distribution,
        # we get no results.
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        vocabulary = DistributionSourcePackageVocabulary(
            context=self.factory.makeDistribution())
        results = vocabulary.searchForTerms(query=bpph.binary_package_name)
        self.assertEqual([], list(results))

    def test_searchForTerms_published_binary(self):
        # We can search for a binary package name, which returns the
        # relevant SPN.
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        distribution = bpph.distroarchseries.distroseries.distribution
        vocabulary = DistributionSourcePackageVocabulary(
            context=distribution)
        spn = bpph.binarypackagerelease.build.source_package_release.name
        results = vocabulary.searchForTerms(query=bpph.binary_package_name)
        self.assertTermsEqual(vocabulary.toTerm(spn), list(results)[0])

    def test_searchForTerms_published_multiple_binaries(self):
        # Searching for a subset of a binary package name returns the SPN
        # that built the binary package.
        spn = self.factory.getOrMakeSourcePackageName('xorg')
        spr = self.factory.makeSourcePackageRelease(sourcepackagename=spn)
        das = self.factory.makeDistroArchSeries()
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr, distroseries=das.distroseries)
        for name in ('xorg-common', 'xorg-server', 'xorg-video-intel'):
            bpn = self.factory.getOrMakeBinaryPackageName(name)
            bpb = self.factory.makeBinaryPackageBuild(
                source_package_release=spr, distroarchseries=das)
            bpr = self.factory.makeBinaryPackageRelease(
                binarypackagename=bpn, build=bpb)
            self.factory.makeBinaryPackagePublishingHistory(
                binarypackagerelease=bpr, distroarchseries=das)
        vocabulary = DistributionSourcePackageVocabulary(
            context=das.distroseries.distribution)
        results = vocabulary.searchForTerms(query='xorg-se')
        self.assertTermsEqual(vocabulary.toTerm(spn), list(results)[0])

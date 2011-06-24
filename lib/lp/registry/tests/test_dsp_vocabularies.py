# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Distribution Source Package vocabulary."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.vocabularies import DistributionSourcePackageVocabulary
from lp.testing import TestCaseWithFactory


class TestDistributionSourcePackageVocabulary(TestCaseWithFactory):
    """Test that the DistributionSourcePackageVocabulary behaves as
    expected."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionSourcePackageVocabulary, self).setUp()
        self.vocabulary = DistributionSourcePackageVocabulary()

    def test_toTerm_unbuilt_dsp(self):
        # If the source has no built binaries, the term's value contains a
        # string to that effect.
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        term = self.vocabulary.toTerm(dsp)
        self.assertEqual(dsp.sourcepackagename.name, term.title)
        expected_token = '%s-%s' % (dsp.distribution.name, dsp.name)
        self.assertEqual(expected_token, term.token)
        self.assertEqual('Not yet built.', term.value)

    def test_toTerm_built_single_binary(self):
        # The binary package name appears in the term's value.
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        spr = bpph.binarypackagerelease.build.source_package_release
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename=spr.sourcepackagename,
            distribution=bpph.distroseries.distribution)
        term = self.vocabulary.toTerm(dsp)
        expected_token = '%s-%s' % (dsp.distribution.name, dsp.name)
        self.assertEqual(expected_token, term.token)
        self.assertEqual(bpph.binary_package_name, term.value)

    def test_toTerm_built_multiple_binary(self):
        # All of the binary package names appear in the term's value.
        spph = self.factory.makeSourcePackagePublishingHistory()
        spr = spph.sourcepackagerelease
        das = self.factory.makeDistroArchSeries(
            distroseries=spph.distroseries)
        expected_names = []
        for i in xrange(20):
            bpb = self.factory.makeBinaryPackageBuild(
                source_package_release=spr, distroarchseries=das)
            bpr = self.factory.makeBinaryPackageRelease(build=bpb)
            expected_names.append(bpr.name)
            self.factory.makeBinaryPackagePublishingHistory(
                binarypackagerelease=bpr, distroarchseries=das)
        dsp = spr.distrosourcepackage
        term = self.vocabulary.toTerm(dsp)
        expected_token = '%s-%s' % (dsp.distribution.name, dsp.name)
        self.assertEqual(expected_token, term.token)
        self.assertEqual(', '.join(expected_names), term.value)

    def test_searchForTerms_None(self):
        # Searching for nothing gets you that.
        results = self.vocabulary.searchForTerms()
        self.assertIs(None, results)

    def assertTermsEqual(self, expected, actual):
        # Assert two given terms are equal.
        self.assertEqual(expected.token, actual.token)
        self.assertEqual(expected.title, actual.title)
        self.assertEqual(expected.value, actual.value)

    def test_searchForTerms_published_source(self):
        # When we search for a source package name that is published, a DSP
        # is returned.
        spph = self.factory.makeSourcePackagePublishingHistory()
        vocabulary = DistributionSourcePackageVocabulary(
            context=spph.distroseries.distribution)
        results = vocabulary.searchForTerms(query=spph.source_package_name)
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename=spph.source_package_name,
            distribution=spph.distroseries.distribution)
        self.assertTermsEqual(vocabulary.toTerm(dsp), results[0])

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
        # We can search for a binary package name, which returns the DSP.
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        distribution = bpph.distroarchseries.distroseries.distribution
        vocabulary = DistributionSourcePackageVocabulary(
            context=distribution)
        spn = bpph.binarypackagerelease.build.source_package_release.name
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename=spn, distribution=distribution)
        results = vocabulary.searchForTerms(query=bpph.binary_package_name)
        self.assertTermsEqual(vocabulary.toTerm(dsp), results[0])

    def test_searchForTerms_published_multiple_binaries(self):
        # Searching for a subset of a binary package name returns the DSP
        # that built the binary package.
        spn = self.factory.getOrMakeSourcePackageName('xorg')
        spr = self.factory.makeSourcePackageRelease(sourcepackagename=spn)
        das = self.factory.makeDistroArchSeries()
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr, distroseries=das.distroseries)
        for name in ('xorg-common', 'xorg-server', 'xorg-video-intel'):
            bpn = self.factory.getOrMakeBinaryPackageName(name)
            bpb = self.factory.makeBinaryPackageBuild(
                source_package_release=spr, distroarchseries=das)
            bpr = self.factory.makeBinaryPackageRelease(
                binarypackagename=bpn, build=bpb)
            bpph = self.factory.makeBinaryPackagePublishingHistory(
                binarypackagerelease=bpr, distroarchseries=das)
        dsp = self.factory.makeDistributionSourcePackage(
            distribution=das.distroseries.distribution,
            sourcepackagename=spn)
        vocabulary = DistributionSourcePackageVocabulary(
            context=das.distroseries.distribution)
        results = vocabulary.searchForTerms(query='xorg-se')
        self.assertTermsEqual(vocabulary.toTerm(dsp), results[0])

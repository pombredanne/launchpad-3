# Copyright 2011-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Distribution Source Package vocabulary."""

__metaclass__ = type

from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.vocabularies import DistributionSourcePackageVocabulary
from lp.services.webapp.vocabulary import IHugeVocabulary
from lp.soyuz.enums import ArchivePurpose
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestDistributionSourcePackageVocabulary(TestCaseWithFactory):
    """Test that the vocabulary behaves as expected."""
    layer = DatabaseFunctionalLayer

    def test_provides_IHugeVocabulary(self):
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
        # A DSP bugtask can be the context.
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo')
        bugtask = self.factory.makeBugTask(target=dsp)
        vocabulary = DistributionSourcePackageVocabulary(bugtask)
        self.assertEqual(bugtask, vocabulary.context)
        self.assertEqual(dsp.distribution, vocabulary.distribution)
        self.assertEqual(dsp, vocabulary.dsp)

    def test_init_dsp_question(self):
        # A DSP bugtask can be the context.
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
        self.assertIsNone(vocabulary.distribution)
        self.assertIsNone(vocabulary.dsp)

    def test_setDistribution(self):
        # Callsites can set the distribution after the vocabulary was
        # instantiated.
        new_distro = self.factory.makeDistribution(name='fnord')
        vocabulary = DistributionSourcePackageVocabulary(None)
        vocabulary.setDistribution(new_distro)
        self.assertEqual(new_distro, vocabulary.distribution)

    def test_contains_true_with_distribution(self):
        # The vocabulary contains official DSPs.
        dsp = self.factory.makeDistributionSourcePackage(with_db=True)
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        self.assertIn(dsp, vocabulary)

    def test_contains_true_with_dsp(self):
        # The vocabulary contains the DSP passed to init when it is not
        # official.
        dsp = self.factory.makeDistributionSourcePackage(with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(dsp)
        self.assertIn(dsp, vocabulary)

    def test_contains_true_with_cacheless_distribution(self):
        # The vocabulary contains DSPs that are not official, provided that
        # the distribution has no cached package names.
        dsp = self.factory.makeDistributionSourcePackage(with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        self.assertIn(dsp, vocabulary)

    def test_contains_false_with_distribution(self):
        # The vocabulary does not contain DSPs that are not official that
        # were not passed to init.
        distro = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(distroseries=distroseries)
        dsp = self.factory.makeDistributionSourcePackage(
            distribution=distro, with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        self.assertNotIn(dsp, vocabulary)

    def test_toTerm_raises_error(self):
        # An error is raised for DSP/SPNs that are not official and are not
        # in the vocabulary.
        distro = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(distroseries=distroseries)
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo', distribution=distro, with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        self.assertRaises(LookupError, vocabulary.toTerm, dsp)

    def test_toTerm_none_raises_error(self):
        # An error is raised for an SPN that does not exist.
        vocabulary = DistributionSourcePackageVocabulary(
            self.factory.makeDistribution())
        self.assertRaises(LookupError, vocabulary.toTerm, 'nonexistent')

    def test_toTerm_spn_and_default_distribution(self):
        # The vocabulary's distribution is used when only a SPN is passed.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.distroseries.distribution.getSourcePackage(
            spph.sourcepackagerelease.sourcepackagename)
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        term = vocabulary.toTerm(dsp.sourcepackagename)
        self.assertEqual(dsp.name, term.token)
        self.assertEqual(dsp.name, term.title)
        self.assertEqual(dsp, term.value)

    def test_toTerm_spn_with_cacheless_distribution(self):
        # An SPN with no official DSP is accepted, provided that the
        # distribution has no cached package names.
        distro = self.factory.makeDistribution()
        spn = self.factory.makeSourcePackageName()
        vocabulary = DistributionSourcePackageVocabulary(distro)
        term = vocabulary.toTerm(spn)
        self.assertEqual(spn.name, term.token)
        self.assertEqual(spn.name, term.title)
        self.assertEqual(distro, term.value.distribution)
        self.assertEqual(spn, term.value.sourcepackagename)

    def test_toTerm_dsp(self):
        # The DSP's distribution is used when a DSP is passed.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.distroseries.distribution.getSourcePackage(
            spph.sourcepackagerelease.sourcepackagename)
        vocabulary = DistributionSourcePackageVocabulary(dsp)
        term = vocabulary.toTerm(dsp)
        self.assertEqual(dsp.name, term.token)
        self.assertEqual(dsp.name, term.title)
        self.assertEqual(dsp, term.value)

    def test_toTerm_dsp_and_binary_names(self):
        # The DSP can be passed with a string on binary names that will be
        # cached as a list in DSP.binary_names.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.distroseries.distribution.getSourcePackage(
            spph.sourcepackagerelease.sourcepackagename)
        vocabulary = DistributionSourcePackageVocabulary(dsp)
        term = vocabulary.toTerm((dsp, 'one two'))
        self.assertEqual(dsp.name, term.token)
        self.assertEqual(dsp.name, term.title)
        self.assertEqual(dsp, term.value)
        self.assertEqual(['one', 'two'], term.value.binary_names)

    def test_toTerm_dsp_with_cacheless_distribution(self):
        # A DSP that is not official is accepted, provided that the
        # distribution has no cached package names.
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo', with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        term = vocabulary.toTerm(dsp)
        self.assertEqual(dsp.name, term.token)
        self.assertEqual(dsp.name, term.title)
        self.assertEqual(dsp, term.value)

    def test_toTerm_dsp_no_distribution(self):
        # The vocabulary can convert a DSP to a term even if it does not yet
        # have a distribution.
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo', with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(None)
        term = vocabulary.toTerm(dsp)
        self.assertEqual(dsp.name, term.token)
        self.assertEqual(dsp.name, term.title)
        self.assertEqual(dsp, term.value)

    def test_getTermByToken_error(self):
        # An error is raised if the token does not match a official DSP.
        distro = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(distroseries=distroseries)
        dsp = self.factory.makeDistributionSourcePackage(
            distribution=distro, sourcepackagename='foo', with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        self.assertRaises(LookupError, vocabulary.getTermByToken, dsp.name)

    def test_getTermByToken_token(self):
        # The term is returned if it matches an official DSP.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.distroseries.distribution.getSourcePackage(
            spph.sourcepackagerelease.sourcepackagename)
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        term = vocabulary.getTermByToken(dsp.name)
        self.assertEqual(dsp, term.value)

    def test_getTermByToken_token_with_cacheless_distribution(self):
        # The term is returned if it does not match an official DSP,
        # provided that the distribution has no cached package names.
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='foo', with_db=False)
        vocabulary = DistributionSourcePackageVocabulary(dsp.distribution)
        term = vocabulary.getTermByToken(dsp.name)
        self.assertEqual(dsp, term.value)

    def test_searchForTerms_without_distribution(self):
        # searchForTerms asserts that the vocabulary has a distribution.
        spph = self.factory.makeSourcePackagePublishingHistory()
        dsp = spph.distroseries.distribution.getSourcePackage(
            spph.sourcepackagerelease.sourcepackagename)
        vocabulary = DistributionSourcePackageVocabulary(dsp.name)
        self.assertRaises(AssertionError, vocabulary.searchForTerms, dsp.name)

    def test_searchForTerms_None(self):
        # Searching for nothing gets you that.
        vocabulary = DistributionSourcePackageVocabulary(
            self.factory.makeDistribution())
        results = vocabulary.searchForTerms()
        self.assertEqual(0, results.count())

    def test_searchForTerms_exact_official_source_name(self):
        # Exact source name matches are found.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf')
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='snarf')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('snarf', terms[0].token)

    def test_searchForTerms_similar_official_source_name(self):
        # Partial source name matches are found.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='pting-snarf-ack')
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='snarf')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('pting-snarf-ack', terms[0].token)

    def test_searchForTerms_exact_binary_name(self):
        # Exact binary name matches are found.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf',
            binary_names='pting-dev pting ack')
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='pting')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('snarf', terms[0].token)

    def test_searchForTerms_similar_binary_name(self):
        # Partial binary name matches are found.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf',
            binary_names='thrpp pting-dev ack')
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='pting')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('snarf', terms[0].token)

    def test_searchForTerms_exact_unofficial_source_name(self):
        # Unofficial source packages are not found by search.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf',
            official=False)
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='snarf')
        terms = list(results)
        self.assertEqual(0, len(terms))

    def test_searchForTerms_similar_unofficial_binary_name(self):
        # Unofficial binary packages are not found by search.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf',
            official=False, binary_names='thrpp pting ack')
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='pting')
        terms = list(results)
        self.assertEqual(0, len(terms))

    def test_searchForTerms_ranking(self):
        # Exact matches are ranked higher than similar matches.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf')
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf-server')
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='pting-devel',
            binary_names='snarf')
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='pting-client',
            binary_names='snarf-common')
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='snarf')
        terms = list(results)
        self.assertEqual(4, len(terms))
        self.assertEqual('snarf', terms[0].token)
        self.assertEqual('pting-devel', terms[1].token)
        self.assertEqual('snarf-server', terms[2].token)
        self.assertEqual('pting-client', terms[3].token)

    def test_searchForTerms_deduplication(self):
        # Search deduplicates cache rows with the same name, e.g. an
        # official source package that also has an official branch.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf')
        branch = self.factory.makePackageBranch(distroseries=distroseries)
        with person_logged_in(distro.owner):
            distroseries.getSourcePackage('snarf').setBranch(
                PackagePublishingPocket.RELEASE, branch, distro.owner)
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='snarf')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('snarf', terms[0].token)

    def test_searchForTerms_partner_archive(self):
        # Packages in partner archives are searched.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf',
            archive=self.factory.makeArchive(
                distribution=distro, purpose=ArchivePurpose.PARTNER))
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='snarf')
        terms = list(results)
        self.assertEqual(1, len(terms))
        self.assertEqual('snarf', terms[0].token)

    def test_searchForTerms_ppa_archive(self):
        # Packages in PPAs are ignored.
        distro = self.factory.makeDistribution(name='fnord')
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename='snarf',
            official=False,
            archive=self.factory.makeArchive(
                distribution=distro, purpose=ArchivePurpose.PPA))
        vocabulary = DistributionSourcePackageVocabulary(distro)
        results = vocabulary.searchForTerms(query='snarf')
        self.assertEqual(0, results.count())

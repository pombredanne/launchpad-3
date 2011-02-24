# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for merging translations."""

__metaclass__ = type


from storm.locals import Store
import transaction

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    )
from lp.registry.model.packagingjob import PackagingJob
from lp.services.job.interfaces.job import IRunnableJob
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.side import TranslationSide
from lp.translations.interfaces.translationpackagingjob import (
    ITranslationPackagingJobSource,
    )
from lp.translations.model.potemplate import POTemplateSubset
from lp.translations.model.translationpackagingjob import (
    TranslationMergeJob,
    TranslationPackagingJob,
    TranslationSplitJob,
    )
from lp.translations.tests.test_translationsplitter import (
    make_shared_potmsgset,
    )


def make_translation_merge_job(factory, not_ubuntu=False):
    singular = factory.getUniqueString()
    upstream_pofile = factory.makePOFile(side=TranslationSide.UPSTREAM)
    upstream_potmsgset = factory.makePOTMsgSet(
        upstream_pofile.potemplate, singular)
    upstream = factory.makeCurrentTranslationMessage(
        pofile=upstream_pofile, potmsgset=upstream_potmsgset)
    if not_ubuntu:
        distroseries = factory.makeDistroSeries()
    else:
        distroseries = factory.makeUbuntuDistroSeries()
    package_potemplate = factory.makePOTemplate(
        distroseries=distroseries, name=upstream_pofile.potemplate.name)
    package_pofile = factory.makePOFile(
        potemplate=package_potemplate, language=upstream_pofile.language)
    package_potmsgset = factory.makePOTMsgSet(
        package_pofile.potemplate, singular)
    package = factory.makeCurrentTranslationMessage(
        pofile=package_pofile, potmsgset=package_potmsgset,
        translations=upstream.translations)
    productseries = upstream_pofile.potemplate.productseries
    distroseries = package_pofile.potemplate.distroseries
    sourcepackagename = package_pofile.potemplate.sourcepackagename
    return TranslationMergeJob.create(
        productseries=productseries, distroseries=distroseries,
        sourcepackagename=sourcepackagename)


def get_msg_sets(productseries=None, distroseries=None,
               sourcepackagename=None):
    msg_sets = []
    for template in POTemplateSubset(
        productseries=productseries, distroseries=distroseries,
        sourcepackagename=sourcepackagename):
        msg_sets.extend(template.getPOTMsgSets())
    return msg_sets


def get_translations(productseries=None, distroseries=None,
                    sourcepackagename=None):
    msg_sets = get_msg_sets(
        productseries=productseries, distroseries=distroseries,
        sourcepackagename=sourcepackagename)
    translations = set()
    for msg_set in msg_sets:
        translations.update(msg_set.getAllTranslationMessages())
    return translations


def count_translations(job):
    tm = get_translations(productseries=job.productseries)
    tm.update(get_translations(
        sourcepackagename=job.sourcepackagename,
        distroseries=job.distroseries))
    return len(tm)


class TestTranslationPackagingJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_interface(self):
        """Should implement ITranslationPackagingJobSource."""
        verifyObject(ITranslationPackagingJobSource, TranslationPackagingJob)


class TestTranslationMergeJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_interface(self):
        """TranslationMergeJob must implement IRunnableJob."""
        job = make_translation_merge_job(self.factory)
        verifyObject(IRunnableJob, job)

    def test_run_merges_msgset(self):
        """Run should merge msgsets."""
        job = make_translation_merge_job(self.factory)
        self.becomeDbUser('rosettaadmin')
        product_msg = get_msg_sets(productseries=job.productseries)
        package_msg = get_msg_sets(
            sourcepackagename=job.sourcepackagename,
            distroseries=job.distroseries)
        self.assertNotEqual(package_msg, product_msg)
        job.run()
        product_msg = get_msg_sets(productseries=job.productseries)
        package_msg = get_msg_sets(
            sourcepackagename=job.sourcepackagename,
            distroseries=job.distroseries)
        self.assertEqual(package_msg, product_msg)

    def test_run_merges_translations(self):
        """Run should merge translations."""
        job = make_translation_merge_job(self.factory)
        self.becomeDbUser('rosettaadmin')
        self.assertEqual(2, count_translations(job))
        job.run()
        self.assertEqual(1, count_translations(job))

    def test_skips_non_ubuntu_distros(self):
        """Run should ignore non-Ubuntu distributions."""
        job = make_translation_merge_job(self.factory, not_ubuntu=True)
        self.becomeDbUser('rosettaadmin')
        self.assertEqual(2, count_translations(job))
        job.run()
        self.assertEqual(2, count_translations(job))

    @staticmethod
    def findJobs(productseries, sourcepackage):
        store = Store.of(productseries)
        result = store.find(
            PackagingJob,
            PackagingJob.productseries_id == productseries.id,
            PackagingJob.sourcepackagename_id ==
            sourcepackage.sourcepackagename.id,
            PackagingJob.distroseries_id ==
            sourcepackage.distroseries.id,
            )
        return list(result)

    def test_create_packaging_makes_job(self):
        """Creating a Packaging should make a TranslationMergeJob."""
        productseries = self.factory.makeProductSeries()
        sourcepackage = self.factory.makeSourcePackage()
        self.assertEqual([], self.findJobs(productseries, sourcepackage))
        sourcepackage.setPackaging(productseries, productseries.owner)
        self.assertNotEqual([], self.findJobs(productseries, sourcepackage))
        # Ensure no constraints were violated.
        transaction.commit()


class TestTranslationSplitJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_run_splits_translations(self):
        upstream_item, ubuntu_item = make_shared_potmsgset(self.factory)
        job = TranslationSplitJob.create(
            upstream_item.potemplate.productseries,
            ubuntu_item.potemplate.distroseries,
            ubuntu_item.potemplate.sourcepackagename,
        )
        self.assertEqual(upstream_item.potmsgset, ubuntu_item.potmsgset)
        job.run()
        self.assertNotEqual(upstream_item.potmsgset, ubuntu_item.potmsgset)

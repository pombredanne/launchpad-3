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
from lp.services.job.interfaces.job import IRunnableJob
from lp.services.job.model.job import Job
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.side import TranslationSide
from lp.translations.interfaces.translationmergejob import (
    ITranslationMergeJobSource,
    )
from lp.translations.model.potemplate import POTemplateSubset
from lp.translations.model.translationmergejob import TranslationMergeJob


def make_translation_merge_job(factory):
    singular = factory.getUniqueString()
    upstream_pofile = factory.makePOFile(side=TranslationSide.UPSTREAM)
    upstream_potmsgset = factory.makePOTMsgSet(
        upstream_pofile.potemplate, singular, sequence=1)
    upstream = factory.makeCurrentTranslationMessage(
        pofile=upstream_pofile, potmsgset=upstream_potmsgset)
    ubuntu_potemplate = factory.makePOTemplate(
        side=TranslationSide.UBUNTU, name=upstream_pofile.potemplate.name)
    ubuntu_pofile = factory.makePOFile(
        potemplate=ubuntu_potemplate, language=upstream_pofile.language)
    ubuntu_potmsgset = factory.makePOTMsgSet(
        ubuntu_pofile.potemplate, singular, sequence=1)
    ubuntu = factory.makeCurrentTranslationMessage(
        pofile=ubuntu_pofile, potmsgset=ubuntu_potmsgset,
        translations=upstream.translations)
    productseries = upstream_pofile.potemplate.productseries
    distroseries = ubuntu_pofile.potemplate.distroseries
    sourcepackagename = ubuntu_pofile.potemplate.sourcepackagename
    return TranslationMergeJob(
        job=Job(), productseries=productseries, distroseries=distroseries,
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


class TestTranslationMergeJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_interface(self):
        """TranslationMergeJob must implement its interfaces."""
        verifyObject(ITranslationMergeJobSource, TranslationMergeJob)
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

    @staticmethod
    def findJobs(productseries, sourcepackage):
        store = Store.of(productseries)
        result = store.find(
            TranslationMergeJob,
            TranslationMergeJob.productseries_id == productseries.id,
            TranslationMergeJob.sourcepackagename_id ==
            sourcepackage.sourcepackagename.id,
            TranslationMergeJob.distroseries_id ==
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

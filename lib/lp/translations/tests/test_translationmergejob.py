# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for merging translations."""

__metaclass__ = type


from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    )
from lp.services.job.interfaces.job import IRunnableJob
from lp.services.job.model.job import Job
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.side import TranslationSide
from lp.translations.model.potemplate import POTemplateSubset
from lp.translations.model.translationmergejob import TranslationMergeJob


class TestTranslationMergeJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    @staticmethod
    def makeTranslationMergeJob(factory):
        singular = factory.getUniqueString()
        upstream_pofile = factory.makePOFile(
            side=TranslationSide.UPSTREAM)
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
            Job(), productseries, distroseries, sourcepackagename)

    def test_interface(self):
        """TranslationMergeJob must implement IRunnableJob."""
        job = self.makeTranslationMergeJob(self.factory)
        verifyObject(IRunnableJob, job)

    @staticmethod
    def getMsgSets(productseries=None, distroseries=None,
                   sourcepackagename=None):
        msg_sets = []
        for template in POTemplateSubset(
            productseries=productseries, distroseries=distroseries,
            sourcepackagename=sourcepackagename):
            msg_sets.extend(template.getPOTMsgSets())
        return msg_sets

    @classmethod
    def getTranslations(cls, productseries=None, distroseries=None,
                        sourcepackagename=None):
        msg_sets = cls.getMsgSets(
            productseries=productseries, distroseries=distroseries,
            sourcepackagename=sourcepackagename)
        translations = set()
        for msg_set in msg_sets:
            translations.update(msg_set.getAllTranslationMessages())
        return translations

    @classmethod
    def countTranslations(cls, job):
        tm = cls.getTranslations(productseries=job.productseries)
        tm.update(cls.getTranslations(
            sourcepackagename=job.sourcepackagename,
            distroseries=job.distroseries))
        return len(tm)

    def test_run_merges_msgset(self):
        """Run should merge msgsets."""
        job = self.makeTranslationMergeJob(self.factory)
        self.becomeDbUser('rosettaadmin')
        product_msg = self.getMsgSets(productseries=job.productseries)
        package_msg = self.getMsgSets(
            sourcepackagename=job.sourcepackagename,
            distroseries=job.distroseries)
        self.assertNotEqual(package_msg, product_msg)
        job.run()
        product_msg = self.getMsgSets(productseries=job.productseries)
        package_msg = self.getMsgSets(
            sourcepackagename=job.sourcepackagename,
            distroseries=job.distroseries)
        self.assertEqual(package_msg, product_msg)

    def test_run_merges_translations(self):
        """Run should merge translations."""
        job = self.makeTranslationMergeJob(self.factory)
        self.becomeDbUser('rosettaadmin')
        self.assertEqual(2, self.countTranslations(job))
        job.run()
        self.assertEqual(1, self.countTranslations(job))

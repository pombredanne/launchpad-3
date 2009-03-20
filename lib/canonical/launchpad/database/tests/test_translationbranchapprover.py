# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Translation File Auto Approver tests."""

__metaclass__ = type

from unittest import TestLoader
from zope.component import getUtility

from canonical.launchpad.interfaces.translationimportqueue import (
    ITranslationImportQueue, RosettaImportStatus)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.database.translationbranchapprover import (
    TranslationBranchApprover)
from canonical.testing import LaunchpadZopelessLayer

class TestTranslationBranchApprover(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.queue = getUtility(ITranslationImportQueue)
        self.series = self.factory.makeProductSeries()
#        LaunchpadZopelessLayer.switchDbUser(config.poimport.dbuser)

    def _setup_none_existent(self, pot_path):
        self.entry = self.queue.addOrUpdateEntry(pot_path,
            self.factory.getUniqueString(), True, self.series.owner,
            productseries=self.series)
        self.approver = TranslationBranchApprover((pot_path,),
                                                  productseries=self.series)

    def test_non_existent_approved(self):
        TRANSLATION_DOMAIN = self.factory.getUniqueString()
        self._setup_none_existent(TRANSLATION_DOMAIN+u'.pot')
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.APPROVED, self.entry.status)

    def test_non_existent_missing_domain(self):
        self._setup_none_existent(u'messages.pot')
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, self.entry.status)

    def test_non_existent_not_a_template(self):
        self._setup_none_existent(u'eo.po')
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, self.entry.status)

    def test_non_existent_domain(self):
        TRANSLATION_DOMAIN = self.factory.getUniqueString()
        self._setup_none_existent(TRANSLATION_DOMAIN+'.pot')
        self.approver.approve(self.entry)
        self.assertEqual(
            TRANSLATION_DOMAIN, self.entry.potemplate.translation_domain)

    def test_non_existent_domain_with_xpi(self):
        TRANSLATION_DOMAIN = self.factory.getUniqueString()
        self._setup_none_existent(
                TRANSLATION_DOMAIN+'/en-US.xpi')
        self.approver.approve(self.entry)
        self.assertEqual(
            TRANSLATION_DOMAIN, self.entry.potemplate.translation_domain)

    def test_template_name(self):
        # The name should not contain underscores any more.
        TRANSLATION_DOMAIN = ('translation_domain_with_underscores')
        TEMPLATE_NAME = TRANSLATION_DOMAIN.replace('_','-')
        self._setup_none_existent(TRANSLATION_DOMAIN+'.pot')
        self.approver.approve(self.entry)
        self.assertEqual(TEMPLATE_NAME, self.entry.potemplate.name)

    def _setup_one_existing(self, domain, pot_path_queue=None):
        pot_path = domain+'.pot'
        if pot_path_queue is None:
            pot_path_queue = pot_path
        self.potemplate = self.factory.makePOTemplate(
            productseries=self.series,
            name=domain.replace('_', '-'), translation_domain=domain,
            path=pot_path)
        self.entry = self.queue.addOrUpdateEntry(pot_path_queue,
            self.factory.getUniqueString(), True, self.series.owner,
            productseries=self.series)
        self.approver = TranslationBranchApprover((pot_path,),
                                                  productseries=self.series)

    def test_replace_existing_approved(self):
        self._setup_one_existing(self.factory.getUniqueString())
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.APPROVED, self.entry.status)

    def test_replace_existing_potemplate(self):
        self._setup_one_existing(self.factory.getUniqueString())
        self.approver.approve(self.entry)
        self.assertEqual(self.potemplate, self.entry.potemplate)

    def test_replace_existing_any_path(self):
        # If just one template file is found in the tree and just one
        # POTEMPLATE object is in the database, the upload is always approved.
        self._setup_one_existing(self.factory.getUniqueString(),
                                 self.factory.getUniqueString()+'.pot')
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.APPROVED, self.entry.status)

    def _setup_add_template(self, new_domain):
        existing_domain = self.factory.getUniqueString()
        existing_path = u"%s/%s.pot" % (existing_domain, existing_domain)
        existing_potemplate = self.factory.makePOTemplate(
            productseries=self.series,
            name=existing_domain.replace('_', '-'),
            translation_domain=existing_domain,
            path=existing_path)
        new_path = u"%s/%s.pot" % (new_domain, new_domain)
        self.entry = self.queue.addOrUpdateEntry(new_path,
            self.factory.getUniqueString(), True, self.series.owner,
            productseries=self.series)
        self.approver = TranslationBranchApprover(
            (new_path,existing_path), productseries=self.series)

    def test_add_approved(self):
        self._setup_add_template(self.factory.getUniqueString())
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.APPROVED, self.entry.status)

    def test_add_potemplate(self):
        TRANSLATION_DOMAIN = self.factory.getUniqueString()
        self._setup_add_template(TRANSLATION_DOMAIN)
        self.approver.approve(self.entry)
        self.assertEqual(
            TRANSLATION_DOMAIN, self.entry.potemplate.translation_domain)

    def test_duplicate_template_name(self):
        POT_PATH1 = "po/foo_domain.pot"
        POT_PATH2 = "foo_domain/messages.pot"
        entry1 = self.queue.addOrUpdateEntry(POT_PATH1,
            self.factory.getUniqueString(), True, self.series.owner,
            productseries=self.series)
        entry2 = self.queue.addOrUpdateEntry(POT_PATH2,
            self.factory.getUniqueString(), True, self.series.owner,
            productseries=self.series)
        approver = TranslationBranchApprover((POT_PATH1, POT_PATH2),
                                             productseries=self.series)
        approver.approve(entry1)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry1.status)
        approver.approve(entry2)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry2.status)

def test_suite():
    return TestLoader().loadTestsFromName(__name__)

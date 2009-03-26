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

    def _upload_template(self, upload_path,
                         existing_domain=None, existing_path=None):
        # Put a template in the import queue and possibly create an existing
        # POTemplate entry in the database.
        if existing_path is None:
            existing_path = upload_path
        if existing_domain is not None:
            self.potemplate = self.factory.makePOTemplate(
                productseries=self.series,
                name=existing_domain.replace('_', '-'),
                translation_domain=existing_domain,
                path=existing_path)
        self.entry = self.queue.addOrUpdateEntry(upload_path,
            self.factory.getUniqueString(), True, self.series.owner,
            productseries=self.series)
        self.approver = TranslationBranchApprover((upload_path,),
                                                  productseries=self.series)

    def test_new_template_approved(self):
        translation_domain = self.factory.getUniqueString()
        self._upload_template(translation_domain + u'.pot')
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.APPROVED, self.entry.status)

    def test_new_template_missing_domain(self):
        self._upload_template(u'messages.pot')
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, self.entry.status)

    def test_new_template_not_a_template(self):
        self._upload_template(u'eo.po')
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, self.entry.status)

    def test_new_template_domain(self):
        translation_domain = self.factory.getUniqueString()
        self._upload_template(translation_domain + '.pot')
        self.approver.approve(self.entry)
        self.assertEqual(
            translation_domain, self.entry.potemplate.translation_domain)

    def test_new_template_domain_with_xpi(self):
        translation_domain = self.factory.getUniqueString()
        self._upload_template(
                translation_domain + '/en-US.xpi')
        self.approver.approve(self.entry)
        self.assertEqual(
            translation_domain, self.entry.potemplate.translation_domain)

    def test_template_name(self):
        # The name should not contain underscores any more.
        translation_domain = ('translation_domain_with_underscores')
        template_name = translation_domain.replace('_', '-')
        self._upload_template(translation_domain + '.pot')
        self.approver.approve(self.entry)
        self.assertEqual(template_name, self.entry.potemplate.name)

    def test_replace_existing_approved(self):
        translation_domain = self.factory.getUniqueString()
        self._upload_template(translation_domain + '.pot', translation_domain)
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.APPROVED, self.entry.status)

    def test_replace_existing_potemplate(self):
        translation_domain = self.factory.getUniqueString()
        self._upload_template(translation_domain + '.pot', translation_domain)
        self.approver.approve(self.entry)
        self.assertEqual(self.potemplate, self.entry.potemplate)

    def test_replace_existing_any_path(self):
        # If just one template file is found in the tree and just one
        # POTemplate object is in the database, the upload is always approved.
        existing_domain = self.factory.getUniqueString()
        self._upload_template(self.factory.getUniqueString() + '.pot',
            existing_domain, existing_domain + '.pot')
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.APPROVED, self.entry.status)

    def test_replace_existing_generic_path_approved(self):
        # If an upload file has a generic path that does not yield a
        # translation domain it is still approved if an entry with the same
        # file name exists.
        existing_domain = self.factory.getUniqueString()
        self._upload_template('po/messages.pot',
                               existing_domain, 'po/messages.pot')
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.APPROVED, self.entry.status)

    def test_replace_existing_generic_path_domain(self):
        # Uploads with a generic path do not overwrite the translation domain
        # on the existing POTemplate entry.
        existing_domain = self.factory.getUniqueString()
        self._upload_template('po/messages.pot',
                               existing_domain, 'po/messages.pot')
        self.approver.approve(self.entry)
        self.assertIsNot(None, self.entry.potemplate)
        self.assertEqual(
            existing_domain, self.entry.potemplate.translation_domain)

    def _upload_second_template(self, new_domain):
        # Upload a second template when there is one in the database already.
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
        self._upload_second_template(self.factory.getUniqueString())
        self.approver.approve(self.entry)
        self.assertEqual(RosettaImportStatus.APPROVED, self.entry.status)

    def test_add_potemplate(self):
        translation_domain = self.factory.getUniqueString()
        self._upload_second_template(translation_domain)
        self.approver.approve(self.entry)
        self.assertEqual(
            translation_domain, self.entry.potemplate.translation_domain)

    def test_duplicate_template_name(self):
        pot_path1 = "po/foo_domain.pot"
        pot_path2 = "foo_domain/messages.pot"
        entry1 = self.queue.addOrUpdateEntry(pot_path1,
            self.factory.getUniqueString(), True, self.series.owner,
            productseries=self.series)
        entry2 = self.queue.addOrUpdateEntry(pot_path2,
            self.factory.getUniqueString(), True, self.series.owner,
            productseries=self.series)
        approver = TranslationBranchApprover((pot_path1, pot_path2),
                                             productseries=self.series)
        approver.approve(entry1)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry1.status)
        approver.approve(entry2)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry2.status)

def test_suite():
    return TestLoader().loadTestsFromName(__name__)

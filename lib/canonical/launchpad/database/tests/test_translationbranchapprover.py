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
        super(TestTranslationBranchApprover, self).setUp()
        self.queue = getUtility(ITranslationImportQueue)
        self.series = self.factory.makeProductSeries()

    def _upload_file(self, upload_path):
        # Put a template or translation file in the import queue.
        return self.queue.addOrUpdateEntry(upload_path,
            self.factory.getUniqueString(), True, self.series.owner,
            productseries=self.series)

    def _create_template(self, path, domain):
        # Create a template in the database
        return self.factory.makePOTemplate(
            productseries=self.series,
            name=domain.replace('_', '-'),
            translation_domain=domain,
            path=path)

    def _create_approver(self, file_or_files):
        if not isinstance(file_or_files, (tuple, list)):
            paths = (file_or_files,)
        else:
            paths = file_or_files
        return TranslationBranchApprover(paths, productseries=self.series)

    def test_new_template_approved(self):
        # The approver puts new entries in the Approved state.
        template_path = self.factory.getUniqueString() + u'.pot'
        entry = self._upload_file(template_path)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry.status)
        approver = self._create_approver(template_path)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)

    def test_new_template_missing_domain(self):
        # A file can only be approved if the file path contains the
        # translation domain and is not generic.
        template_path = u'messages.pot'
        entry = self._upload_file(template_path)
        approver = self._create_approver(template_path)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry.status)

    def test_new_template_not_a_template(self):
        # Only template files will be approved currently.
        path = u'eo.po'
        entry = self._upload_file(path)
        approver = self._create_approver(path)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry.status)

    def test_new_template_domain(self):
        # The approver gets the translation domain for the entry from the
        # file path.
        translation_domain = self.factory.getUniqueString()
        template_path = translation_domain + u'.pot'
        entry = self._upload_file(template_path)
        approver = self._create_approver(template_path)
        approver.approve(entry)
        self.assertEqual(
            translation_domain, entry.potemplate.translation_domain)

    def test_new_template_domain_with_xpi(self):
        # For xpi files the domain is taken from the directory.
        translation_domain = self.factory.getUniqueString()
        template_path = translation_domain + '/en-US.xpi'
        entry = self._upload_file(template_path)
        approver = self._create_approver(template_path)
        approver.approve(entry)
        self.assertEqual(
            translation_domain, entry.potemplate.translation_domain)

    def test_template_name(self):
        # The name should not contain underscores any more.
        translation_domain = ('translation_domain_with_underscores')
        template_name = translation_domain.replace('_', '-')
        template_path = translation_domain + u'.pot'
        entry = self._upload_file(template_path)
        approver = self._create_approver(template_path)
        approver.approve(entry)
        self.assertEqual(template_name, entry.potemplate.name)

    def test_replace_existing_approved(self):
        # Template files that replace existing entries are approved.
        translation_domain = self.factory.getUniqueString()
        template_path = translation_domain + u'.pot'
        self._create_template(template_path, translation_domain)
        entry = self._upload_file(template_path)
        approver = self._create_approver(template_path)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)

    def test_replace_existing_potemplate(self):
        # When replacing an existing template, the queue entry is linked to
        # that existing entry.
        translation_domain = self.factory.getUniqueString()
        template_path = translation_domain + u'.pot'
        potemplate = self._create_template(template_path, translation_domain)
        entry = self._upload_file(template_path)
        approver = self._create_approver(template_path)
        approver.approve(entry)
        self.assertEqual(potemplate, entry.potemplate)

    def test_replace_existing_any_path(self):
        # If just one template file is found in the tree and just one
        # POTemplate object is in the database, the upload is always approved.
        existing_domain = self.factory.getUniqueString()
        existing_path = existing_domain + u'.pot'
        potemplate = self._create_template(existing_path, existing_domain)
        template_path = self.factory.getUniqueString() + u'.pot'
        entry = self._upload_file(template_path)
        approver = self._create_approver(template_path)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)
        self.assertEqual(potemplate, entry.potemplate)

    def test_replace_existing_generic_path_approved(self):
        # If an upload file has a generic path that does not yield a
        # translation domain it is still approved if an entry with the same
        # file name exists.
        translation_domain = self.factory.getUniqueString()
        generic_path = u'po/messages.pot'
        potemplate = self._create_template(generic_path, translation_domain)
        entry = self._upload_file(generic_path)
        approver = self._create_approver(generic_path)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)

    def test_replace_existing_generic_path_domain(self):
        # Uploads with a generic path do not overwrite the translation domain
        # on the existing POTemplate entry.
        translation_domain = self.factory.getUniqueString()
        generic_path = u'po/messages.pot'
        potemplate = self._create_template(generic_path, translation_domain)
        entry = self._upload_file(generic_path)
        approver = self._create_approver(generic_path)
        approver.approve(entry)
        self.assertEqual(
            translation_domain, entry.potemplate.translation_domain)

    def test_add_template(self):
        # When adding a template to an existing one it is approved if the
        # approver is told about both template files in the tree.
        existing_domain = self.factory.getUniqueString()
        existing_path = u"%s/%s.pot" % (existing_domain, existing_domain)
        self._create_template(existing_path, existing_domain)
        new_domain = self.factory.getUniqueString()
        new_path = u"%s/%s.pot" % (new_domain, new_domain)
        entry = self._upload_file(new_path)
        approver = self._create_approver((existing_path, new_path))
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)
        self.assertEqual(new_domain, entry.potemplate.translation_domain)

    def test_upload_multiple_new_templates(self):
        # Multiple new templates can be added using the same
        # TranslationBranchApprover instance.
        pot_path1 = self.factory.getUniqueString() + ".pot"
        pot_path2 = self.factory.getUniqueString() + ".pot"
        entry1 = self._upload_file(pot_path1)
        entry2 = self._upload_file(pot_path2)
        approver = self._create_approver((pot_path1, pot_path2))
        approver.approve(entry1)
        self.assertEqual(RosettaImportStatus.APPROVED, entry1.status)
        approver.approve(entry2)
        self.assertEqual(RosettaImportStatus.APPROVED, entry2.status)

    def test_duplicate_template_name(self):
        pot_path1 = "po/foo_domain.pot"
        pot_path2 = "foo_domain/messages.pot"
        entry1 = self._upload_file(pot_path1)
        entry2 = self._upload_file(pot_path2)
        approver = self._create_approver((pot_path1, pot_path2))
        approver.approve(entry1)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry1.status)
        approver.approve(entry2)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry2.status)

def test_suite():
    return TestLoader().loadTestsFromName(__name__)

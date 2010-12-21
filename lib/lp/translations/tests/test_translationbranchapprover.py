# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translation File Auto Approver tests."""

__metaclass__ = type

from unittest import TestLoader

import transaction
from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.validators.name import valid_name
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory
from lp.translations.enums import RosettaImportStatus
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )
from lp.translations.model.approver import TranslationBranchApprover


def become_the_approver(layer):
    """Switch to the branch-approver's database user identity."""
    transaction.commit()
    layer.switchDbUser('translationsbranchscanner')


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

    def _createTemplate(self, path, domain, productseries=None):
        # Create a template in the database
        if productseries is None:
            productseries = self.series
        return self.factory.makePOTemplate(
            productseries=productseries,
            name=domain.replace('_', '-'),
            translation_domain=domain,
            path=path)

    def _createApprover(self, file_or_files):
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
        approver = self._createApprover(template_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)

    def test_new_template_missing_domain(self):
        # A file can only be approved if the file path contains the
        # translation domain and is not generic.
        template_path = u'messages.pot'
        entry = self._upload_file(template_path)
        approver = self._createApprover(template_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry.status)

    def test_new_template_not_a_template(self):
        # Only template files will be approved currently.
        path = u'eo.po'
        entry = self._upload_file(path)
        approver = self._createApprover(path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry.status)

    def test_new_template_domain(self):
        # The approver gets the translation domain for the entry from the
        # file path.
        translation_domain = self.factory.getUniqueString()
        template_path = translation_domain + u'.pot'
        entry = self._upload_file(template_path)
        approver = self._createApprover(template_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(
            translation_domain, entry.potemplate.translation_domain)

    def test_new_template_domain_with_xpi(self):
        # For xpi files the domain is taken from the directory.
        translation_domain = self.factory.getUniqueString()
        template_path = translation_domain + '/en-US.xpi'
        entry = self._upload_file(template_path)
        approver = self._createApprover(template_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(
            translation_domain, entry.potemplate.translation_domain)

    def test_template_name(self):
        # The name is derived from the file name and must be a valid name.
        translation_domain = (u'Invalid-Name_with illegal#Characters')
        template_path = translation_domain + u'.pot'
        entry = self._upload_file(template_path)
        approver = self._createApprover(template_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertTrue(valid_name(entry.potemplate.name))
        self.assertEqual(u'invalid-name-withillegalcharacters',
                         entry.potemplate.name)

    def test_replace_existing_approved(self):
        # Template files that replace existing entries are approved.
        translation_domain = self.factory.getUniqueString()
        template_path = translation_domain + u'.pot'
        self._createTemplate(template_path, translation_domain)
        entry = self._upload_file(template_path)
        approver = self._createApprover(template_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)

    def test_replace_existing_potemplate(self):
        # When replacing an existing template, the queue entry is linked to
        # that existing entry.
        translation_domain = self.factory.getUniqueString()
        template_path = translation_domain + u'.pot'
        potemplate = self._createTemplate(template_path, translation_domain)
        entry = self._upload_file(template_path)
        approver = self._createApprover(template_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(potemplate, entry.potemplate)

    def test_replace_existing_any_path(self):
        # If just one template file is found in the tree and just one
        # POTemplate object is in the database, the upload is always approved.
        existing_domain = self.factory.getUniqueString()
        existing_path = existing_domain + u'.pot'
        potemplate = self._createTemplate(existing_path, existing_domain)
        template_path = self.factory.getUniqueString() + u'.pot'
        entry = self._upload_file(template_path)
        approver = self._createApprover(template_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)
        self.assertEqual(potemplate, entry.potemplate)

    def test_replace_existing_generic_path_approved(self):
        # If an upload file has a generic path that does not yield a
        # translation domain it is still approved if an entry with the same
        # file name exists.
        translation_domain = self.factory.getUniqueString()
        generic_path = u'po/messages.pot'
        self._createTemplate(generic_path, translation_domain)
        entry = self._upload_file(generic_path)
        approver = self._createApprover(generic_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)

    def test_replace_existing_generic_path_domain(self):
        # Uploads with a generic path do not overwrite the translation domain
        # on the existing POTemplate entry.
        translation_domain = self.factory.getUniqueString()
        generic_path = u'po/messages.pot'
        self._createTemplate(generic_path, translation_domain)
        entry = self._upload_file(generic_path)
        approver = self._createApprover(generic_path)

        become_the_approver(self.layer)
        approver.approve(entry)
        self.assertEqual(
            translation_domain, entry.potemplate.translation_domain)

    def test_add_template(self):
        # When adding a template to an existing one it is approved if the
        # approver is told about both template files in the tree.
        existing_domain = self.factory.getUniqueString()
        existing_path = u"%s/%s.pot" % (existing_domain, existing_domain)
        self._createTemplate(existing_path, existing_domain)
        new_domain = self.factory.getUniqueString()
        new_path = u"%s/%s.pot" % (new_domain, new_domain)
        entry = self._upload_file(new_path)
        approver = self._createApprover((existing_path, new_path))

        become_the_approver(self.layer)
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
        approver = self._createApprover((pot_path1, pot_path2))

        become_the_approver(self.layer)
        approver.approve(entry1)
        self.assertEqual(RosettaImportStatus.APPROVED, entry1.status)
        approver.approve(entry2)
        self.assertEqual(RosettaImportStatus.APPROVED, entry2.status)

    def test_duplicate_template_name(self):
        # If two templates in the branch indicate the same translation
        # domain they are in conflict and will not be approved.
        pot_path1 = "po/foo_domain.pot"
        pot_path2 = "foo_domain/messages.pot"
        entry1 = self._upload_file(pot_path1)
        entry2 = self._upload_file(pot_path2)
        approver = self._createApprover((pot_path1, pot_path2))

        become_the_approver(self.layer)
        approver.approve(entry1)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry1.status)
        approver.approve(entry2)
        self.assertEqual(RosettaImportStatus.NEEDS_REVIEW, entry2.status)

    def test_approve_only_if_needs_review(self):
        # If an entry is not in NEEDS_REVIEW state, it must not be approved.
        pot_path = self.factory.getUniqueString() + ".pot"
        entry = self._upload_file(pot_path)
        entry.potemplate = self.factory.makePOTemplate()
        not_approve_status = (
            RosettaImportStatus.IMPORTED,
            RosettaImportStatus.DELETED,
            RosettaImportStatus.FAILED,
            RosettaImportStatus.BLOCKED,
            )
        for status in not_approve_status:
            entry.setStatus(
                status, getUtility(ILaunchpadCelebrities).rosetta_experts)
            approver = self._createApprover(pot_path)
            approver.approve(entry)
            self.assertEqual(status, entry.status)

    def test_approveNewSharingTemplate(self):
        # When the approver creates a new template, the new template
        # gets copies of any existing POFiles for templates that it will
        # share translations with.
        domain = self.factory.getUniqueString()
        pot_path = domain + ".pot"
        trunk = self.series.product.getSeries('trunk')
        trunk_template = self._createTemplate(
            pot_path, domain=domain, productseries=trunk)
        dutch_pofile = self.factory.makePOFile(
            'nl', potemplate=trunk_template)
        entry = self._upload_file(pot_path)
        approver = self._createApprover(pot_path)

        become_the_approver(self.layer)
        approver.approve(entry)

        # This really did create a new template.
        self.assertNotEqual(None, entry.potemplate)
        self.assertNotEqual(trunk_template, entry.potemplate)
        self.assertEqual(trunk_template.name, entry.potemplate.name)

        # The new template also has a Dutch translation of its own.
        new_dutch_pofile = entry.potemplate.getPOFileByLang('nl')
        self.assertNotEqual(None, new_dutch_pofile)
        self.assertNotEqual(dutch_pofile, new_dutch_pofile)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

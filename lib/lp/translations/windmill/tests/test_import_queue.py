# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for translation import queue entry approving behaviour."""

__metaclass__ = type
__all__ = []

import transaction
from zope.component import getUtility

from canonical.launchpad.webapp import canonical_url
from lp.app.enums import ServiceUsage
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    SLEEP,
    )
from lp.testing.windmill.lpuser import login_person
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )
from lp.translations.windmill.testing import TranslationsWindmillLayer


class ImportQueueEntryTest(WindmillTestCase):
    """Test that the entries in the import queue can switch types."""

    layer = TranslationsWindmillLayer
    suite_name = 'Translations import queue entry'

    FIELDS = {
        'POT': [
            'field.potemplate',
            'field.name',
            'field.translation_domain',
            ],
        'PO': [
            'field.potemplate',
            'field.potemplate_name',
            'field.language',
            ],
        }
    SELECT_FIELDS = [
        'field.potemplate',
        'field.language',
    ]

    def _getHiddenTRXpath(self, field_id):
        if field_id in self.SELECT_FIELDS:
            input_tag = 'select'
        else:
            input_tag = 'input'
        return (
            u"//tr[contains(@class,'unseen')]"
            u"//%s[@id='%s']" % (input_tag, field_id))

    def _assertAllFieldsVisible(self, client, fields):
        """Assert that all given fields are visible.

        Fields are visible if they do not have the "unseen" class set.
        """
        for field_id in fields:
            client.asserts.assertNotNode(
                xpath=self._getHiddenTRXpath(field_id))

    def _assertAllFieldsHidden(self, client, fields):
        """Assert that all given fields are hidden.

        Fields are hidden if they have the "unseen" class set.
        """
        for field_id in fields:
            client.asserts.assertNode(
                xpath=self._getHiddenTRXpath(field_id))

    def test_import_queue_entry(self):
        """Tests that import queue entry fields behave correctly."""
        client = self.client
        start_url = '%s/+imports/1' % TranslationsWindmillLayer.base_url
        user = lpuser.TRANSLATIONS_ADMIN
        # Go to import queue page logged in as translations admin.
        user.ensure_login(client)
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)

        po_only_fields = set(self.FIELDS['PO']) - set(self.FIELDS['POT'])
        pot_only_fields = set(self.FIELDS['POT']) - set(self.FIELDS['PO'])

        # When the page is first called the file_type is set to POT and
        # only the relevant form fields are displayed. When the file type
        # select box is changed to PO, other fields are shown hidden while
        # the first ones are hidden. Finally, all fields are hidden if the
        # file type is unspecified.
        client.waits.forElement(id=u'field.file_type', timeout=FOR_ELEMENT)
        client.asserts.assertSelected(id=u'field.file_type', validator=u'POT')
        self._assertAllFieldsVisible(client, self.FIELDS['POT'])
        self._assertAllFieldsHidden(client, po_only_fields)

        client.select(id=u'field.file_type', val=u'PO')
        self._assertAllFieldsVisible(client, self.FIELDS['PO'])
        self._assertAllFieldsHidden(client, pot_only_fields)

        client.select(id=u'field.file_type', val=u'UNSPEC')
        self._assertAllFieldsHidden(client, self.FIELDS['POT'])
        self._assertAllFieldsHidden(client, self.FIELDS['PO'])

    def test_import_queue_entry_template_selection_new_path(self):
        # For template uploads, the template dropdown controls the
        # template name & translation domain fields.  This saves the
        # trouble of finding the exact strings when approving an update
        # with path changes.
        # If the upload's path does not match any existing templates,
        # the dropdown has no template pre-selected.

        # A productseries has two templates.
        template1 = self.factory.makePOTemplate(
            path='1.pot', name='name1', translation_domain='domain1')
        productseries = template1.productseries
        template2 = self.factory.makePOTemplate(
            path='2.pot', name='name2', translation_domain='domain2')

        # A new template upload for that entry has a path that doesn't
        # match either of the existing templates.
        base_filename = self.factory.getUniqueString(prefix='x')
        path = base_filename + '.pot'
        entry = self.factory.makeTranslationImportQueueEntry(
            path=path, productseries=productseries)
        url = canonical_url(entry, rootsite='translations')

        transaction.commit()

        # The client reviews the upload.
        client = self.client
        user = lpuser.TRANSLATIONS_ADMIN
        user.ensure_login(client)
        client.open(url=url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.sleep(milliseconds=SLEEP)

        # No template is preselected in the templates dropdown.
        client.asserts.assertSelected(id=u'field.potemplate', validator=u'')

        # The template name and translation domain are pre-set to a
        # guess based on the base filename.
        client.asserts.assertValue(
            id=u'field.name', validator=base_filename)
        client.asserts.assertValue(
            id=u'field.translation_domain', validator=base_filename)

        # The user edits the name and translation domain.
        client.type(id=u'field.name', text='new-name')
        client.type(id=u'field.translation_domain', text='new-domain')

        # The user selects an existing template from the dropdown.  This
        # updates the name and domain fields.
        client.select(id=u'field.potemplate', option=u'name1')
        client.asserts.assertValue(id=u'field.name', validator='name1')
        client.asserts.assertValue(
            id=u'field.translation_domain', validator='domain1')

        # When the user returns the dropbox to its original state, the
        # last-entered name and domain come back.
        client.select(id=u'field.potemplate', option=u'')
        client.asserts.assertValue(id=u'field.name', validator='new-name')
        client.asserts.assertValue(
            id=u'field.translation_domain', validator='new-domain')

        # Changing the name and domain to those of an existing domain
        # also updates the dropdown.
        client.type(id=u'field.name', text=u'name1')
        client.type(id=u'field.translation_domain', text=u'domain1')
        client.asserts.assertSelected(
            id=u'field.potemplate', validator=u'name1')

    def test_import_queue_entry_template_selection_existing_path(self):
        # If a template upload's base path matches the name/domain of an
        # existing template, the templates dropdown has that template
        # pre-selected.
        template_name = self.factory.getUniqueString(prefix='x')
        path = template_name + '.pot'
        template = self.factory.makePOTemplate(
            path=path, name=template_name, translation_domain=template_name)

        # A new template upload for that entry has a path that doesn't
        # match either of the existing templates.
        entry = self.factory.makeTranslationImportQueueEntry(
            path=path, productseries=template.productseries,
            distroseries=template.distroseries,
            sourcepackagename=template.sourcepackagename)
        url = canonical_url(entry, rootsite='translations')

        transaction.commit()

        # The client reviews the upload.
        client = self.client
        user = lpuser.TRANSLATIONS_ADMIN
        user.ensure_login(client)
        client.open(url=url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.sleep(milliseconds=SLEEP)

        # The matching template is preselected in the templates dropdown.
        client.asserts.assertSelected(
            id=u'field.potemplate', validator=template_name)

    def test_import_queue_entry_template_selection_escape(self):
        # The potemplate dropdown for templates escapes its strings.
        template = self.factory.makePOTemplate(
            path='quote.pot', name='quote', translation_domain="\\'")

        # A new template upload for that entry has a path that doesn't
        # match either of the existing templates.
        entry = self.factory.makeTranslationImportQueueEntry(
            path='foo.pot', productseries=template.productseries,
            distroseries=template.distroseries,
            sourcepackagename=template.sourcepackagename)
        url = canonical_url(entry, rootsite='translations')

        transaction.commit()

        client = self.client
        user = lpuser.TRANSLATIONS_ADMIN
        user.ensure_login(client)
        client.open(url=url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.sleep(milliseconds=SLEEP)

        client.select(id=u'field.potemplate', option=u'quote')

        client.asserts.assertValue(
            id=u'field.translation_domain', validator=u"\\'")


IMPORT_STATUS = u"//tr[@id='%d']//span[contains(@class,'status-choice')]"
IMPORT_STATUS_1 = IMPORT_STATUS % 1
OPEN_CHOICELIST = u"//div[contains(@class, 'yui3-ichoicelist-content')]"


class ImportQueueStatusTest(WindmillTestCase):
    """Test that the entries in the import queue can switch types."""

    layer = TranslationsWindmillLayer
    suite_name = 'Translations import queue status'

    def test_import_queue_status_admin(self):
        """Tests that the admin can use the status picker."""
        client = self.client
        queue_url = self.layer.base_url+'/+imports'
        user = lpuser.TRANSLATIONS_ADMIN
        # Go to import queue page logged in as translations admin.
        client.open(url=queue_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        user.ensure_login(client)

        # Click on the element containing the import status.
        client.waits.forElement(xpath=IMPORT_STATUS_1, timeout=FOR_ELEMENT)
        client.click(xpath=IMPORT_STATUS_1)
        client.waits.forElement(xpath=OPEN_CHOICELIST)

        # Change the status to deleted.
        client.click(link=u'Deleted')
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(xpath=IMPORT_STATUS_1, validator=u'Deleted')

        # Reload the page and make sure the change sticks.
        client.open(url=queue_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(xpath=IMPORT_STATUS_1, timeout=FOR_ELEMENT)
        client.asserts.assertText(xpath=IMPORT_STATUS_1, validator=u'Deleted')

    def test_import_queue_status_nopriv(self):
        """Tests that a none-admin will have less choices."""
        client = self.client
        queue_url = self.layer.base_url+'/+imports'
        hubert = self.factory.makePerson(
            name="hubert", displayname="Hubert Hunt", password="test",
            email="hubert@example.com")
        # Create a project and an import entry with it.
        product = self.factory.makeProduct(
            owner=hubert,
            translations_usage=ServiceUsage.LAUNCHPAD)
        productseries = product.getSeries('trunk')
        queue = getUtility(ITranslationImportQueue)
        potemplate = self.factory.makePOTemplate(productseries=productseries)
        entry = queue.addOrUpdateEntry(
            'template.pot', '# POT content', False, hubert,
            productseries=productseries, potemplate=potemplate)
        transaction.commit()
        import_status = IMPORT_STATUS % entry.id

        # Go to import queue page logged in as a normal user.
        client.open(url=queue_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        login_person(hubert, "hubert@example.com", "test", client)

        # There should be no status picker for entry 1.
        client.waits.forElement(xpath=import_status, timeout=FOR_ELEMENT)
        client.asserts.assertNotNode(xpath=IMPORT_STATUS_1)

        # Click on the element containing the import status.
        client.click(xpath=import_status)
        client.waits.forElement(xpath=OPEN_CHOICELIST)

        # There should be a link for Deleted but none for approved.
        client.asserts.assertNode(link=u'Deleted')
        client.asserts.assertNotNode(link=u'Approved')

        # Change the status to deleted.
        client.click(link=u'Deleted')
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(xpath=import_status, validator=u'Deleted')

        # Reload the page and make sure the change sticks.
        client.open(url=queue_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(xpath=import_status, timeout=FOR_ELEMENT)
        client.asserts.assertText(xpath=import_status, validator=u'Deleted')

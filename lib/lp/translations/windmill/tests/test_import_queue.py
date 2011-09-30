# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for translation import queue entry approving behaviour."""

__metaclass__ = type
__all__ = []

import transaction
from zope.component import getUtility

from lp.app.enums import ServiceUsage
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    SLEEP,
    )
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )
from lp.translations.windmill.testing import TranslationsWindmillLayer


IMPORT_STATUS = u"//tr[@id='%d']//span[contains(@class,'status-choice')]"
IMPORT_STATUS_1 = IMPORT_STATUS % 1
OPEN_CHOICELIST = u"//div[contains(@class, 'yui3-ichoicelist-content')]"


class ImportQueueStatusTest(WindmillTestCase):
    """Test that the entries in the import queue can switch types."""

    layer = TranslationsWindmillLayer
    suite_name = 'Translations import queue status'

    def test_import_queue_status_admin(self):
        """Tests that the admin can use the status picker."""

        # Go to import queue page logged in as translations admin.
        client, start_url = self.getClientFor(
            '/+imports', user=lpuser.TRANSLATIONS_ADMIN)

        # Click on the element containing the import status.
        client.waits.forElement(xpath=IMPORT_STATUS_1, timeout=FOR_ELEMENT)
        client.click(xpath=IMPORT_STATUS_1)
        client.waits.forElement(xpath=OPEN_CHOICELIST)

        # Change the status to deleted.
        client.click(link=u'Deleted')
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertText(xpath=IMPORT_STATUS_1, validator=u'Deleted')

        # Reload the page and make sure the change sticks.
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(xpath=IMPORT_STATUS_1, timeout=FOR_ELEMENT)
        client.asserts.assertText(xpath=IMPORT_STATUS_1, validator=u'Deleted')

    def test_import_queue_status_nopriv(self):
        """Tests that a none-admin will have less choices."""
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
        client, start_url = self.getClientForPerson('/+imports', hubert)

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
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(xpath=import_status, timeout=FOR_ELEMENT)
        client.asserts.assertText(xpath=import_status, validator=u'Deleted')

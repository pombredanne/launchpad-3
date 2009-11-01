# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for translation import queue entry approving behaviour."""

__metaclass__ = type
__all__ = []

from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser
from lp.translations.windmill.testing import TranslationsWindmillLayer
from lp.testing import TestCaseWithFactory

class ImportQueueEntryTest(TestCaseWithFactory):
    """Test that the entries in the import queue can switch types."""

    layer = TranslationsWindmillLayer

    FIELDS = {
        'POT': [
            'field.name',
            'field.translation_domain',
            ],
        'PO': [
            'field.potemplate',
            'field.potemplate_name',
            'field.language',
            'field.variant',
            ]
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
            u"//tr[contains(@class,'dont_show_fields')]"
            u"//%s[@id='%s']" % (input_tag, field_id)
                )

    def _assertAllFieldsVisible(self, client, groupname):
        """Assert that all fields in this group are visible.

        Fields are visible if they do not have the dont_show_fields
        class set.
        """
        for field_id in self.FIELDS[groupname]:
            client.asserts.assertNotNode(
                xpath=self._getHiddenTRXpath(field_id))

    def _assertAllFieldsHidden(self, client, groupname):
        """Assert that all fields in this group are hidden.

        Fields are hidden if they have the dont_show_fields class set.
        """
        for field_id in self.FIELDS[groupname]:
            client.asserts.assertNode(
                xpath=self._getHiddenTRXpath(field_id))

    def test_import_queue_entry(self):
        """Tests that import queue entry fields behave correctly."""
        client = WindmillTestClient('Translations import queue entry')
        start_url = 'http://translations.launchpad.dev:8085/+imports/1'
        user = lpuser.TRANSLATIONS_ADMIN
        # Go to import queue page logged in as translations admin.
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=u'20000')
        user.ensure_login(client)

        # When the page is first called the file_type is set to POT and
        # only the relevant form fields are displayed. When the file type
        # select box is changed to PO, other fields are shown hidden while
        # the first ones are hidden. Finally, all fields are hidden if the
        # file type is unspecified.
        client.waits.forElement(id=u'field.file_type', timeout=u'8000')
        client.asserts.assertSelected(id=u'field.file_type',
                                           validator=u'POT')
        self._assertAllFieldsVisible(client, 'POT')
        self._assertAllFieldsHidden(client, 'PO')

        client.select(id=u'field.file_type', val=u'PO')
        self._assertAllFieldsVisible(client, 'PO')
        self._assertAllFieldsHidden(client, 'POT')

        client.select(id=u'field.file_type', val=u'UNSPEC')
        self._assertAllFieldsHidden(client, 'POT')
        self._assertAllFieldsHidden(client, 'PO')

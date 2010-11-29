# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translation File Importer tests."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.librarian.testing.fake import FakeLibrarian
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.registry.interfaces.person import IPersonSet
from lp.testing import TestCaseWithFactory
from lp.translations.enums import TranslationPermission
from lp.translations.interfaces.translationimporter import (
    OutdatedTranslationError,
    )
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )
from lp.translations.utilities.gettext_po_importer import GettextPOImporter
from lp.translations.utilities.translation_common_format import (
    TranslationMessageData)
from lp.translations.utilities.translation_import import (
    FileImporter,
    POFileImporter,
    POTFileImporter,
    )


TEST_LANGUAGE = "eo"
TEST_MSGID = "Thank You"
TEST_MSGSTR = "Dankon"
TEST_MSGSTR2 = "Dankon al vi"
TEST_EXPORT_DATE = '"X-Launchpad-Export-Date: 2008-11-05 13:31+0000\\n"\n'
TEST_EXPORT_DATE_EARLIER = (
                   '"X-Launchpad-Export-Date: 2008-11-05 13:20+0000\\n"\n')
NUMBER_OF_TEST_MESSAGES = 1
TEST_TEMPLATE = r'''
msgid ""
msgstr ""
"PO-Revision-Date: 2005-05-03 20:41+0100\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Content-Type: text/plain; charset=UTF-8\n"
%s
msgid "%s"
msgstr ""
'''
TEST_TEMPLATE_EXPORTED = TEST_TEMPLATE % (TEST_EXPORT_DATE, TEST_MSGID)
TEST_TEMPLATE_PUBLISHED = TEST_TEMPLATE % ("", TEST_MSGID)

TEST_TRANSLATION_FILE = r'''
msgid ""
msgstr ""
"PO-Revision-Date: 2008-11-05 13:22+0000\n"
"Last-Translator: Someone New <someone.new@canonical.com>\n"
"Content-Type: text/plain; charset=UTF-8\n"
%s
msgid "%s"
msgstr "%s"
'''
TEST_TRANSLATION_EXPORTED = TEST_TRANSLATION_FILE % (
    TEST_EXPORT_DATE, TEST_MSGID, TEST_MSGSTR)
TEST_TRANSLATION_PUBLISHED = TEST_TRANSLATION_FILE % (
    "", TEST_MSGID, TEST_MSGSTR)
# This is needed for test_FileImporter_importFile_conflict and differs from
# the others in export timestamp and msgstr content.
TEST_TRANSLATION_EXPORTED_EARLIER = TEST_TRANSLATION_FILE % (
    TEST_EXPORT_DATE_EARLIER, TEST_MSGID, TEST_MSGSTR2)

# The following two are needed for test_FileImporter_importFile_error.
# The translation file has an error in the format specifiers.
TEST_MSGID_ERROR = "format specifier follows %d"
TEST_TEMPLATE_FOR_ERROR = r'''
msgid ""
msgstr ""
"PO-Revision-Date: 2005-05-03 20:41+0100\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Content-Type: text/plain; charset=UTF-8\n"

#, c-format
msgid "%s"
msgstr ""
''' % TEST_MSGID_ERROR


TEST_TRANSLATION_FILE_WITH_ERROR = r'''
msgid ""
msgstr ""
"PO-Revision-Date: 2008-09-17 20:41+0100\n"
"Last-Translator: Foo Bar <foo.bar@canonical.com>\n"
"Content-Type: text/plain; charset=UTF-8\n"
"X-Launchpad-Export-Date: 2008-11-05 13:31+0000\n"

#, c-format
msgid "%s"
msgstr "format specifier changes %%s"
''' % TEST_MSGID_ERROR


class FileImporterTestCase(TestCaseWithFactory):
    """Class test for translation importer component"""
    layer = ZopelessDatabaseLayer

    def _createFileImporters(self, pot_content, po_content, is_published):
        """Create queue entries from POT and PO content strings.
        Create importers from the entries."""
        pot_importer = self._createPOTFileImporter(
            pot_content, is_published)
        po_importer = self._createPOFileImporter(
            pot_importer, po_content, is_published)
        return (pot_importer, po_importer)

    def _createPOTFileImporter(self, pot_content, is_published):
        """Create queue entries from POT content string.
        Create an importer from the entry."""
        potemplate = self.factory.makePOTemplate()
        template_entry = self.translation_import_queue.addOrUpdateEntry(
            potemplate.path, pot_content,
            is_published, self.importer_person,
            productseries=potemplate.productseries,
            potemplate=potemplate)
        self.fake_librarian.pretendCommit()
        return POTFileImporter(template_entry, GettextPOImporter(), None)

    def _createPOFileImporter(self,
            pot_importer, po_content, is_published, existing_pofile=None,
            person=None):
        """Create a PO entry from content, relating to a template_entry.
        Create an importer for the entry."""
        potemplate = pot_importer.translation_import_queue_entry.potemplate
        if existing_pofile == None:
            pofile = self.factory.makePOFile(
                TEST_LANGUAGE, potemplate=potemplate)
        else:
            pofile = existing_pofile
        person = person or self.importer_person
        translation_entry = self.translation_import_queue.addOrUpdateEntry(
            pofile.path, po_content, is_published, person,
            productseries=potemplate.productseries, pofile=pofile)
        self.fake_librarian.pretendCommit()
        return POFileImporter(translation_entry, GettextPOImporter(), None)

    def _createImporterForExportedEntries(self):
        """Set up entries that where exported from LP, i.e. that contain the
        'X-Launchpad-Export-Date:' header."""
        return self._createFileImporters(
            TEST_TEMPLATE_EXPORTED, TEST_TRANSLATION_EXPORTED, False)

    def _createImporterForPublishedEntries(self):
        """Set up entries that where not exported from LP, i.e. that do not
        contain the 'X-Launchpad-Export-Date:' header."""
        return self._createFileImporters(
            TEST_TEMPLATE_PUBLISHED, TEST_TRANSLATION_PUBLISHED, True)

    def _createFileImporter(self):
        """Create just an (incomplete) FileImporter for basic tests.
        The importer is based on a template.
        These tests don't care about Imported or Published."""
        potemplate = self.factory.makePOTemplate()
        template_entry = self.translation_import_queue.addOrUpdateEntry(
            potemplate.path, TEST_TEMPLATE_EXPORTED,
            False, self.importer_person,
            productseries=potemplate.productseries,
            potemplate=potemplate)
        self.fake_librarian.pretendCommit()
        return FileImporter(template_entry, GettextPOImporter(), None)

    def setUp(self):
        super(FileImporterTestCase, self).setUp()
        self.fake_librarian = self.useFixture(FakeLibrarian())
        self.translation_import_queue = getUtility(ITranslationImportQueue)
        self.importer_person = self.factory.makePerson()

    def test_FileImporter_importMessage_NotImplemented(self):
        importer = self._createFileImporter()
        self.failUnlessRaises(NotImplementedError,
            importer.importMessage, None)

    def test_FileImporter_format_exporter(self):
        # Test if format_exporter behaves like a singleton
        importer = self._createFileImporter()
        self.failUnless(importer._cached_format_exporter is None,
            "FileImporter._cached_format_exporter was not None, "
            "although it had not been used yet.")

        format_exporter1 = importer.format_exporter
        self.failUnless(format_exporter1 is not None,
            "FileImporter.format_exporter was not instantiated on demand.")

        format_exporter2 = importer.format_exporter
        self.failUnless(format_exporter1 is format_exporter2,
            "FileImporter.format_exporter was instantiated multiple time, "
            "but should have been cached.")

    def test_FileImporter_getOrCreatePOTMsgSet(self):
        pot_importer = self._createPOTFileImporter(
            TEST_TEMPLATE_EXPORTED, False)
        # There is another test (init) to make sure this works.
        message = pot_importer.translation_file.messages[0]
        # Try to get the potmsgset by hand to verify it is not already in
        # the DB
        potmsgset1 = (
            pot_importer.potemplate.getPOTMsgSetByMsgIDText(
                message.msgid_singular, plural_text=message.msgid_plural,
                context=message.context))
        self.failUnless(potmsgset1 is None,
            "IPOTMsgSet object already existed in DB, unable to test "
            "FileImporter.getOrCreatePOTMsgSet")

        potmsgset1 = pot_importer.getOrCreatePOTMsgSet(message)
        self.failUnless(potmsgset1 is not None,
            "FileImporter.getOrCreatePOTMessageSet did not create a new "
            "IPOTMsgSet object in the database.")

        potmsgset2 = pot_importer.getOrCreatePOTMsgSet(message)
        self.failUnlessEqual(potmsgset1.id, potmsgset2.id,
            "FileImporter.getOrCreatePOTMessageSet did not get an existing "
            "IPOTMsgSet object from the database.")

    def _test_storeTranslationsInDatabase_empty(self, is_published=True):
        """Check whether we store empty messages appropriately."""
        # Construct a POFile importer.
        pot_importer = self._createPOTFileImporter(
            TEST_TEMPLATE_EXPORTED, is_published=True)
        importer = self._createPOFileImporter(
            pot_importer, TEST_TRANSLATION_EXPORTED,
            is_published=is_published, person=self.importer_person)

        # Empty message to import.
        message = TranslationMessageData()
        message.addTranslation(0, u'')

        potmsgset = self.factory.makePOTMsgSet(
            potemplate = importer.potemplate, sequence=50)
        translation = importer.storeTranslationsInDatabase(
            message, potmsgset)
        # No TranslationMessage is created.
        self.assertIs(None, translation)

    def test_storeTranslationsInDatabase_empty_imported(self):
        """Storing empty messages for published imports appropriately."""
        self._test_storeTranslationsInDatabase_empty(is_published=True)

    def test_storeTranslationsInDatabase_empty_user(self):
        """Store empty messages for user uploads appropriately."""
        self._test_storeTranslationsInDatabase_empty(is_published=False)

    def test_FileImporter_storeTranslationsInDatabase_privileges(self):
        """Test `storeTranslationsInDatabase` privileges."""

        # On a published import, unprivileged person can still store
        # translations if they were able to add an entry to the queue.
        unprivileged_person = self.factory.makePerson()

        # Steps:
        #  * Get a POT importer and import a POT file.
        #  * Get a POTMsgSet in the imported template.
        #  * Create a published PO file importer with unprivileged
        #    person as the importer.
        #  * Make sure this person lacks editing permissions.
        #  * Try storing translations and watch it succeed.
        #
        pot_importer = self._createPOTFileImporter(
            TEST_TEMPLATE_EXPORTED, True)
        pot_importer.importFile()
        product = pot_importer.potemplate.productseries.product
        product.translationpermission = TranslationPermission.CLOSED
        product.translationgroup = self.factory.makeTranslationGroup(
            self.importer_person)
        self.fake_librarian.pretendCommit()

        # Get one POTMsgSet to do storeTranslationsInDatabase on.
        message = pot_importer.translation_file.messages[0]
        potmsgset = (
            pot_importer.potemplate.getPOTMsgSetByMsgIDText(
                message.msgid_singular, plural_text=message.msgid_plural,
                context=message.context))

        po_importer = self._createPOFileImporter(
            pot_importer, TEST_TRANSLATION_EXPORTED, is_published=True,
            person=unprivileged_person)

        entry = removeSecurityProxy(
            po_importer.translation_import_queue_entry)
        entry.importer = po_importer.translation_import_queue_entry.importer
        is_editor = po_importer.pofile.canEditTranslations(
            unprivileged_person)
        self.assertFalse(is_editor,
            "Unprivileged person is a translations editor.")

        translation_message = po_importer.translation_file.messages[0]
        db_message = po_importer.storeTranslationsInDatabase(
            translation_message, potmsgset)
        self.assertNotEqual(db_message, None)

    def test_FileImporter_init(self):
        (pot_importer, po_importer) = self._createImporterForExportedEntries()
        # The number of test messages is constant (see above).
        self.failUnlessEqual(
            len(pot_importer.translation_file.messages),
            NUMBER_OF_TEST_MESSAGES,
            "FileImporter.__init__ did not parse the template file "
            "correctly.")
        # Test if POTFileImporter gets initialised correctly.
        self.failUnless(pot_importer.potemplate is not None,
            "POTFileImporter had no reference to an IPOTemplate.")
        self.failUnless(pot_importer.pofile is None or
            pot_importer.pofile.language == "en",
            "POTFileImporter referenced an IPOFile which was not English.")
        # Test if POFileImporter gets initialised correctly.
        self.failUnless(po_importer.potemplate is not None,
            "POTFileImporter had no reference to an IPOTemplate.")
        self.failUnless(po_importer.pofile is not None,
            "POFileImporter had no reference to an IPOFile.")

    def test_FileImporter_getPersonByEmail(self):
        (pot_importer, po_importer) = self._createImporterForExportedEntries()
        # Check whether we create new persons with the correct explanation.
        # When importing a POFile, it may be necessary to create new Person
        # entries, to represent the last translators of that POFile.
        test_email = 'danilo@canonical.com'
        personset = getUtility(IPersonSet)

        # The account we are going to use is not yet in Launchpad.
        self.failUnless(
            personset.getByEmail(test_email) is None,
            'There is already an account for %s' % test_email)

        person = po_importer._getPersonByEmail(test_email)

        self.failUnlessEqual(
            person.creation_rationale.name, 'POFILEIMPORT',
            '%s was not created due to a POFile import' % test_email)
        self.failUnlessEqual(
            person.creation_comment,
            'when importing the %s translation of %s' % (
                po_importer.pofile.language.displayname,
                po_importer.potemplate.displayname),
            'Did not create the correct comment for %s' % test_email)

    def test_getPersonByEmail_personless_account(self):
        # An Account without a Person attached is a difficult case for
        # _getPersonByEmail: it has to create the Person but re-use an
        # existing Account and email address.
        (pot_importer, po_importer) = self._createImporterForExportedEntries()
        test_email = 'freecdsplease@example.com'
        account = self.factory.makeAccount('Send me Ubuntu', test_email)

        person = po_importer._getPersonByEmail(test_email)

        self.assertEqual(account, person.account)

        # The same person will come up for the same address next time.
        self.assertEqual(person, po_importer._getPersonByEmail(test_email))

    def test_getPersonByEmail_bad_address(self):
        # _getPersonByEmail returns None for malformed addresses.
        (pot_importer, po_importer) = self._createImporterForExportedEntries()
        test_email = 'john over at swansea'

        person = po_importer._getPersonByEmail(test_email)

        self.assertEqual(None, person)

    def test_FileImporter_importFile_ok(self):
        # Test correct import operation for both
        # exported and published files.
        importers = (
            self._createImporterForExportedEntries(),
            self._createImporterForPublishedEntries(),
            )
        for (pot_importer, po_importer) in importers:
            # Run the import and see if PotMsgSet and TranslationMessage
            # entries are correctly created in the DB.
            errors, warnings = pot_importer.importFile()
            self.failUnlessEqual(len(errors), 0,
                "POTFileImporter.importFile returned errors where there "
                "should be none.")
            potmsgset = pot_importer.potemplate.getPOTMsgSetByMsgIDText(
                                                                TEST_MSGID)
            self.failUnless(potmsgset is not None,
                "POTFileImporter.importFile did not create an IPOTMsgSet "
                "object in the database.")

            errors, warnings = po_importer.importFile()
            self.failUnlessEqual(len(errors), 0,
                "POFileImporter.importFile returned errors where there "
                "should be none.")
            potmsgset = po_importer.pofile.potemplate.getPOTMsgSetByMsgIDText(
                                                        unicode(TEST_MSGID))
            message = potmsgset.getCurrentTranslationMessage(
                po_importer.potemplate, po_importer.pofile.language)
            self.failUnless(message is not None,
                "POFileImporter.importFile did not create an "
                "ITranslationMessage object in the database.")

    def test_FileImporter_importFile_conflict(self):
        (pot_importer, po_importer) = (
            self._createImporterForExportedEntries())
        # Use importFile to store a template and a translation.
        # Then try to store a different translation for the same msgid
        # with an earlier export timestamp to provoke an update conflict.

        # First import template.
        errors, warnings = pot_importer.importFile()
        self.failUnlessEqual(len(errors), 0,
            "POTFileImporter.importFile returned errors where there should "
            "be none.")
        # Now import translation.
        errors, warnings = po_importer.importFile()
        self.failUnlessEqual(len(errors), 0,
            "POFileImporter.importFile returned errors where there should "
            "be none.")
        self.fake_librarian.pretendCommit()

        # Create new POFileImporter with an earlier timestamp and
        # a different translation (msgstr).
        po_importer2 = self._createPOFileImporter(
            pot_importer, TEST_TRANSLATION_EXPORTED_EARLIER, False,
            po_importer.pofile)
        # Try to import this, too.
        errors, warnings = po_importer2.importFile()
        self.failUnlessEqual(len(errors), 1,
            "No error detected when importing a pofile with an earlier "
            "export timestamp (update conflict).")
        self.failUnless(
            errors[0]['error-message'].find(
                u"updated by someone else after you") != -1,
            "importFile() failed to detect a message update conflict.")

    def test_FileImporter_importFile_error(self):
        # Test that gettextpo.error is handled correctly during import.
        # This is done by trying to store a translation (msgstr) with format
        # spefifiers that do not match those in the msgid, as they should.
        (pot_importer, po_importer) = self._createFileImporters(
            TEST_TEMPLATE_FOR_ERROR,
            TEST_TRANSLATION_FILE_WITH_ERROR, False)
        errors, warnings = pot_importer.importFile()
        self.failUnlessEqual(len(errors), 0,
            "POTFileImporter.importFile returned errors where there should "
            "be none.")
        errors, warnings = po_importer.importFile()
        self.failUnlessEqual(len(errors), 1,
            "No error detected when importing a pofile with mismatched "
            "format specifiers.")
        self.failUnless(errors[0]['error-message'].find(
                u"format specifications in 'msgid' and 'msgstr' "
                u"for argument 1 are not the same") != -1,
            "importFile() failed to detect mismatched format specifiers "
            "when importing a pofile.")
        # Although the message has an error, it should still be stored
        # in the database, though only as a suggestion.
        potmsgset = po_importer.pofile.potemplate.getPOTMsgSetByMsgIDText(
            unicode(TEST_MSGID_ERROR))
        message = potmsgset.getLocalTranslationMessages(
            po_importer.potemplate, po_importer.pofile.language)[0]
        self.failUnless(message is not None,
            "POFileImporter.importFile did not create an "
            "ITranslationMessage object with format errors in the database.")

    def test_ValidationErrorPlusConflict(self):
        # Sometimes a conflict is detected when we resubmit a message as
        # a suggestion because it failed validation.  We don't much care
        # what happens to it, so long as the import doesn't bomb out and
        # the message doesn't become a current translation.
        (pot_importer, po_importer) = self._createFileImporters(
                TEST_TEMPLATE_FOR_ERROR,
                TEST_TRANSLATION_FILE_WITH_ERROR, False)
        pot_importer.importFile()
        po_importer.importFile()
        self.fake_librarian.pretendCommit()

        po_importer2 = self._createPOFileImporter(
            pot_importer, TEST_TRANSLATION_EXPORTED_EARLIER, False,
            po_importer.pofile)
        po_importer2.importFile()

        potmsgset = po_importer.pofile.potemplate.getPOTMsgSetByMsgIDText(
            unicode(TEST_MSGID_ERROR))
        messages = potmsgset.getLocalTranslationMessages(
            po_importer.pofile.potemplate, po_importer.pofile.language)

        for message in messages:
            if message.potmsgset.msgid_singular.msgid == TEST_MSGID_ERROR:
                # This is the accursed message.  Whatever happens, it
                # must not be set as the current translation.
                self.assertFalse(message.is_current)
            else:
                # This is the other message that the doomed message
                # conflicted with.
                self.assertEqual(
                    message.potmsgset.msgid_singular.msgid, TEST_MSGID)
                self.assertEqual(message.translations, [TEST_MSGSTR2])

    def test_InvalidTranslatorEmail(self):
        # A Last-Translator with invalid email address does not upset
        # the importer.  It just picks the uploader as the last
        # translator.
        pot_content = TEST_TEMPLATE_PUBLISHED
        po_content = """
            msgid ""
            msgstr ""
            "PO-Revision-Date: 2005-05-03 20:41+0100\\n"
            "Last-Translator: Hector Atlas <??@??.??>\\n"
            "Content-Type: text/plain; charset=UTF-8\\n"
            "X-Launchpad-Export-Date: 2008-11-05 13:31+0000\\n"

            msgid "%s"
            msgstr "Dankuwel"
            """ % TEST_MSGID
        (pot_importer, po_importer) = self._createFileImporters(
            pot_content, po_content, False)
        pot_importer.importFile()

        po_importer.importFile()
        self.assertEqual(
            po_importer.last_translator,
            po_importer.translation_import_queue_entry.importer)


class CreateFileImporterTestCase(TestCaseWithFactory):
    """Class test for translation importer creation."""
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(CreateFileImporterTestCase, self).setUp()
        self.fake_librarian = self.useFixture(FakeLibrarian())
        self.translation_import_queue = getUtility(ITranslationImportQueue)
        self.importer_person = self.factory.makePerson()

    def _make_queue_entry(self, is_published):
        pofile = self.factory.makePOFile('eo')
        # Create a header with a newer date than what is found in
        # TEST_TRANSLATION_FILE.
        pofile.header = ("PO-Revision-Date: 2009-01-05 13:22+0000\n"
                         "Content-Type: text/plain; charset=UTF-8\n")
        po_content = TEST_TRANSLATION_FILE % ("", "foo", "bar")
        queue_entry = self.translation_import_queue.addOrUpdateEntry(
            pofile.path, po_content, is_published, self.importer_person,
            productseries=pofile.potemplate.productseries, pofile=pofile)
        self.fake_librarian.pretendCommit()
        return queue_entry

    def test_raises_OutdatedTranslationError_on_user_uploads(self):
        queue_entry = self._make_queue_entry(False)
        self.assertRaises(
            OutdatedTranslationError,
            POFileImporter, queue_entry, GettextPOImporter(), None)

    def test_not_raises_OutdatedTranslationError_on_published_uploads(self):
        queue_entry = self._make_queue_entry(True)
        try:
            importer = POFileImporter(queue_entry, GettextPOImporter(), None)
        except OutdatedTranslationError:
            self.fail("OutdatedTranslationError raised.")

    def test_old_published_upload_not_changes_header(self):
        queue_entry = self._make_queue_entry(True)
        pofile = queue_entry.pofile
        old_raw_header = pofile.header
        importer = POFileImporter(queue_entry, GettextPOImporter(), None)
        self.assertEqual(old_raw_header, pofile.header)

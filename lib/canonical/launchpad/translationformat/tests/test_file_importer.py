# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Translation File Importer tests."""

__metaclass__ = type

import unittest
import transaction
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IPersonSet, ITranslationImportQueue)
from canonical.launchpad.testing import (
    LaunchpadObjectFactory)
from canonical.launchpad.translationformat.gettext_po_importer import (
    GettextPOImporter)
from canonical.launchpad.translationformat.translation_import import (
    FileImporter, POTFileImporter, POFileImporter)
from canonical.testing import LaunchpadZopelessLayer

TEST_LANGUAGE = "eo"
TEST_MSGID = "Thank You"
TEST_TRANSLATION = "Dankon"
NUMBER_OF_TEST_MESSAGES = 1
TEST_TEMPLATE = r'''
msgid ""
msgstr ""
"PO-Revision-Date: 2005-05-03 20:41+0100\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Content-Type: text/plain; charset=UTF-8\n"

msgid "%s"
msgstr ""
''' % (TEST_MSGID)

TEST_TRANSLATION_FILE = r'''
msgid ""
msgstr ""
"PO-Revision-Date: 2008-09-17 20:41+0100\n"
"Last-Translator: Foo Bar <foo.bar@canonical.com>\n"
"Content-Type: text/plain; charset=UTF-8\n"

msgid "%s"
msgstr "%s"
''' % (TEST_MSGID, TEST_TRANSLATION)

class FileImporterTestCase(unittest.TestCase):
    """Class test for translation importer component"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        factory = LaunchpadObjectFactory()
        # Add a new entry for testing purposes. It's a template one.
        self.translation_import_queue = getUtility(ITranslationImportQueue)
        is_published = True
        importer_person = factory.makePerson()
        self.potemplate = factory.makePOTemplate()
        self.pofile = factory.makePOFile(
            TEST_LANGUAGE, potemplate=self.potemplate)
        self.template_entry = self.translation_import_queue.addOrUpdateEntry(
            self.potemplate.path, TEST_TEMPLATE,
            is_published, importer_person,
            productseries=self.potemplate.productseries,
            potemplate=self.potemplate)

        # Add another one, a translation file.
        translation_entry = self.translation_import_queue.addOrUpdateEntry(
            self.pofile.path, TEST_TRANSLATION_FILE,
            is_published, importer_person,
            productseries=self.potemplate.productseries,
            pofile=self.pofile)

        transaction.commit()

        # Create objects to test
        self.file_importer = FileImporter(
            self.template_entry, GettextPOImporter(), None )
        self.pot_importer = POTFileImporter(
            self.template_entry, GettextPOImporter(), None )
        self.po_importer = POFileImporter(
            translation_entry, GettextPOImporter(), None )

    def test_fileImporter_init(self):
        # The number of test messages is constant (see above).
        self.failUnlessEqual(
            len(self.file_importer.translation_file.messages),
            NUMBER_OF_TEST_MESSAGES,
            "FileImporter.__init__ did not parse the template file "
            "correctly.")

    def test_fileImporter_importMessage(self):
        self.failUnlessRaises( NotImplementedError,
            self.file_importer.importMessage, None)

    def test_fileImporter_importFile(self):
        # import File calls importMethod which should raise the exception.
        self.failUnlessRaises( NotImplementedError,
            self.file_importer.importFile)

    def test_fileImporter_getOrCreatePOTMsgSet(self):
        # Set the potemplate instance, usually done by subclass
        self.file_importer.potemplate = self.potemplate
        # There is another test (init) to make sure this works.
        message = self.file_importer.translation_file.messages[0]
        # Try to get the potmsgset by hand to verify it is not already in
        # the DB
        potmsgset1 = (
            self.potemplate.getPOTMsgSetByMsgIDText(
                message.msgid_singular, plural_text=message.msgid_plural,
                context=message.context))
        self.failUnless(potmsgset1 is None,
            "IPOTMsgSet object already exists in DB, unable to test "
            "FileImporter.getOrCreatePOTMsgSet")

        potmsgset1 = self.file_importer.getOrCreatePOTMsgSet(message)
        self.failUnless(potmsgset1 is not None,
            "FileImporter.getOrCreatePOTMessageSet did not create a new "
            "IPOTMsgSet object in the database.")

        potmsgset2 = self.file_importer.getOrCreatePOTMsgSet(message)
        self.failUnlessEqual(potmsgset1.id, potmsgset2.id,
            "FileImporter.getOrCreatePOTMessageSet did not get an existing "
            "IPOTMsgSet object from the database.")

    def test_fileImporter_storeTranslationsInDatabase(self):
        # Set the potemplate instance, usually done by subclass
        self.file_importer.potemplate = self.potemplate
        # There is another test (init) to make sure this works.
        message = self.file_importer.translation_file.messages[0]
        # There is another test (getOrCreatePOTMsgSet) to make sure this
        # works.
        potmsgset = self.file_importer.getOrCreatePOTMsgSet(message)

        retval = self.file_importer.storeTranslationsInDatabase(
            message, potmsgset)
        self.failUnless( retval is None,
            "FileImporter.storeTranslationsInDatabase tries to store data "
            "without refrence to an IPOFile.")

        # Perform a sanity check for empty errors list
        self.failUnlessEqual(len(self.file_importer.errors), 0,
            "FileImporter.errors list is not empty, although freshly "
            "initialised.")

        # Complete necessary attributes, usually done by subclass
        self.file_importer.pofile = self.pofile
        self.file_importer.is_editor = True
        self.file_importer.last_translator = self.template_entry.importer

        # Test for normal operation
        retval = self.file_importer.storeTranslationsInDatabase(
            message, potmsgset)
        self.failUnless(
            (retval is not None) and
            (len(self.file_importer.errors) == 0),
            "FileImporter.storeTranslationsInDatabase fails when storing "
            "a message without errors.")

# TODO: henninge 2008-10-02 Make storeTranslationsInDatabase reject a
#  translation because of a conflict.
# TODO: henninge 2008-10-02 Make storeTranslationsInDatabase accept a
#  translation with error.

    def test_fileImporter_format_exporter(self):
        # Test if format_exporter behaves like a singleton
        self.failUnless(self.file_importer._cached_format_exporter is None,
            "FileImporter._cached_format_exporter is not None, "
            "although it has not been used yet.")

        format_exporter1 = self.file_importer.format_exporter
        self.failUnless(format_exporter1 is not None,
            "FileImporter.format_exporter is not instantiated on demand.")

        format_exporter2 = self.file_importer.format_exporter
        self.failUnless(format_exporter1 is format_exporter2,
            "FileImporter.format_exporter is instantiated multiple time, "
            "but should be cached.")

    def test_POTFileImporter_init(self):
        # Test if POTFileImporter gets initialised correctly.
        self.failUnless(self.pot_importer.potemplate is not None,
            "POTFileImporter has no reference to an IPOTemplate.")
        self.failUnless(self.pot_importer.pofile is None or
            self.pot_importer.pofile.language == "en",
            "POTFileImporter references an IPOFile which is not English." )

    def test_POTFileImporter_importMessage_implemented(self):
        # The class must implement importMessage and not throw
        # NotImplementedError like the base class does.
        try:
            self.pot_importer.importMessage(None)
        except NotImplementedError:
            self.fail("POTFileImporter does not implement importMessage()")
        except:
            pass

    def test_POTFileImporter_importFile(self):
        # Run the whole show and see what comes out.
        errors = self.pot_importer.importFile()
        self.failUnlessEqual(len(errors), 0,
            "POTFileImporter.importFile returns errors where there should "
            "be none.")
        potmsgset = self.potemplate.getPOTMsgSetByMsgIDText(TEST_MSGID)
        self.failUnless(potmsgset is not None,
            "POTFileImporter.importFile does not create an IPOTMsgSet "
            "object in the database.")

    def test_POFileImporter_init(self):
        # Test if POFileImporter gets initialised correctly.
        self.failUnless(self.po_importer.potemplate is not None,
            "POTFileImporter has no reference to an IPOTemplate.")
        self.failUnless(self.po_importer.pofile is not None,
            "POFileImporter has no reference to an IPOFile.")

    def test_POFileImporter_importMessage(self):
        # The class must implement importMessage and not throw
        # NotImplementedError like the base class does.
        try:
            self.po_importer.importMessage(None)
        except NotImplementedError:
            self.fail("POFileImporter does not implement importMessage()")
        except:
            pass

    def test_POFileImporter_getPersonByEmail(self):
        # Check whether we create new persons with the correct explanation.
        # When importing a POFile, it may be necessary to create new Person
        # entries, to represent the last translators of that POFile.
        test_email = 'danilo@canonical.com'
        personset = getUtility(IPersonSet)

        # The account we are going to use is not yet in Launchpad.
        self.failUnless(
            personset.getByEmail(test_email) is None,
            'There is already an account for %s' % test_email)

        person = self.po_importer._getPersonByEmail(test_email)

        self.failUnlessEqual(
            person.creation_rationale.name, 'POFILEIMPORT',
            '%s was not created due to a POFile import' % test_email)
        self.failUnlessEqual(
            person.creation_comment,
            'when importing the %s translation of %s' % (
                self.po_importer.pofile.language.displayname,
                self.po_importer.potemplate.displayname),
            'Did not create the correct comment for %s' % test_email)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FileImporterTestCase))
    return suite

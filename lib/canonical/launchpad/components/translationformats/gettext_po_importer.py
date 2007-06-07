# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TranslationFormatImporter'
    ]

import os.path
from email.Utils import parseaddr
from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces import ITranslationFormatImporter
from canonical.launchpad.components.poparser import POParser
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lp.dbschema import RosettaFileFormat, RosettaImportStatus


class TranslationFormatImporter:
    """Support class to import gettext .po files."""
    implements(ITranslationFormatImporter)

    def __init__(self, translation_import_queue_entry, logger=None):
        self.basepath = translation_import_queue_entry.path
        self.productseries = translation_import_queue_entry.productseries
        self.distrorelease = translation_import_queue_entry.distrorelease
        self.sourcepackagename = (
            translation_import_queue_entry.sourcepackagename)
        self.is_published = translation_import_queue_entry.is_published
        self.logger = logger

        librarian_client = getUtility(ILibrarianClient)
        self.content = librarian_client.getFileByAlias(
            translation_import_queue_entry.content.id)

    @cachedproperty
    def format(self):
        """See ITranslationImporter."""
        return RosettaFileFormat.PO

    @property
    def allentries(self):
        """See ITranslationImporter."""
        filename = self.basepath.lower()
        if filename.endswith('.pot'):
            language = None
        elif filename.endswith('.po'):
            language = os.path.basename(self.basepath)[:-3]
        else:
            return None


        entries = [ { 'path' : self.basepath,
                      'productseries' : self.productseries,
                      'distrorelease' : self.distrorelease,
                      'sourcepackagename' : self.sourcepackagename,
                      'is_published' : self.is_published,
                      'template' : self.sourcepackagename,
                      'language' : language,
                      'importer' : None,
                      'state' : RosettaImportStatus.NEEDS_REVIEW,
                      'format' : RosettaFileFormat.PO } ]
        return entries

    def canHandleFileExtension(self, extension):
        """See ITranslationImporter."""
        return extension in ['.po', '.pot']

    def getLastTranslator(self, parser):
        """Return the person that appears as Last-Translator in a PO file.

        Returns a tuple containing name and email address.
        """
        if parser.header is None:
            # The file does not have a header field.
            return None

        try:
            last_translator = parser.header['Last-Translator']
        except KeyError:
            # Usually we should only get a KeyError exception but if we get
            # any other exception we should do the same, use the importer name
            # as the person who owns the imported po file.
            return None

        name, email = parseaddr(last_translator)

        if email == 'EMAIL@ADDRESS' or not '@' in email:
            # Gettext (and Rosetta) sets by default the email address to
            # EMAIL@ADDRESS unless we know the real address, thus, we know this
            # isn't a real account and we use the person that imported the file
            # as the owner.
            return None
        else:
            return (name, email)

    def getTemplate(self, path):
        parser = POParser()
        parser.write(self.content)
        parser.finish()

        translator_name = translator_email = None

        errors = []
        msgs = []
        for pomessage in parser.messages:
            message = {}
            message['msgid'] = pomessage.msgid
            message['msgid_plural'] = pomessage.msgidPlural
            message['comment'] = pomessage.commentText
            message['sourcecomment'] = pomessage.sourceComment
            message['filerefs'] = pomessage.fileReferences
            message['flags'] = pomessage.flags
            message['obsolete'] = pomessage.obsolete
            message['msgstr'] = None

            msgs.append(message)

        return {
            "revisiondate" : None,
            "lasttranslatoremail" : translator_email,
            "lasttranslatorname" : translator_name,
            "header" : parser.header,
            "messages" : msgs,
            "format" : RosettaFileFormat.PO
            }

    def getTranslation(self, path, language):
        parser = POParser()
        parser.write(self.content)
        parser.finish()

        last_translator = self.getLastTranslator(parser)
        if last_translator:
            translator_name = last_translator[0]
            translator_email = last_translator[1]
        else:
            translator_name = translator_email = None

        errors = []
        msgs = []
        for pomessage in parser.messages:
            message = {}
            message['msgid'] = pomessage.msgid
            message['msgid_plural'] = pomessage.msgidPlural
            message['comment'] = pomessage.commentText
            message['sourcecomment'] = pomessage.sourceComment
            message['filerefs'] = pomessage.fileReferences
            message['flags'] = pomessage.flags
            message['obsolete'] = pomessage.obsolete

            if pomessage.msgstrPlurals:
                translations = {}
                for i, plural in enumerate(pomessage.msgstrPlurals):
                    translations[i] = plural
            elif pomessage.msgstr is not None:
                translations = { 0: pomessage.msgstr }
            else:
                # We don't have anything to import.
                translations = None

            message['msgstr'] = translations

            msgs.append(message)

        return {
            "revisiondate" : None,
            "lasttranslatoremail" : translator_email,
            "lasttranslatorname" : translator_name,
            "header" : parser.header,
            "messages" : msgs,
            "format" : RosettaFileFormat.PO
            }



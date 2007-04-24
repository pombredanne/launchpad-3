# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'PoSupport'
    ]

import datetime
import pytz
from email.Utils import parseaddr
from zope.interface import implements
from canonical.launchpad.interfaces import ITranslationImport
from canonical.launchpad.components.poparser import POParser
from canonical.lp.dbschema import RosettaFileFormat

class PoSupport:
    implements(ITranslationImport)

    def __init__(self, path, productseries=None, distrorelease=None,
                 sourcepackagename=None, is_published=False, content=None,
                 logger=None):
        self.basepath = path
        self.productseries = productseries
        self.distrorelease = distrorelease
        self.sourcepackagename = sourcepackagename
        self.is_published = is_published
        self.content = content
        self.logger = logger

    @property
    def allentries(self):
        """See ITranslationImport."""

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



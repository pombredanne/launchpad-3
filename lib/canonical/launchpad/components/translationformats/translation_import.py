# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TranslationImporter',
    ]

import gettextpo
import datetime
import pytz
from email.Utils import parseaddr
from zope.component import getUtility
from sqlobject import SQLObjectNotFound

from canonical.config import config
from canonical.launchpad.interfaces import (
        IPOTemplate, IPOFile, IPersonSet, ITranslationImporter,
        TranslationConstants, TranslationConflict, OldTranslationImported,
        NotExportedFromLaunchpad)
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lp.dbschema import (
    RosettaFileFormat, PersonCreationRationale)
from canonical.launchpad.webapp import canonical_url


class TranslationImporter:
    implements(ITranslationImporter)

    def __init__(self):
        self.pofile = None
        self.potemplate = None

    def getPersonByEmail(self, email, name=None):
        """Return the person for given email.

        :arg email: text that contains the email address.
        :arg name: name of the owner of the give email address.

        If the person is unknown in launchpad, the account will be created.
        """
        assert self.pofile is not None

        if not email or email == 'EMAIL@ADDRESS' or not '@' in email:
            # EMAIL@ADDRESS is a well known default value for email address so
            # we ignore it.
            return None

        personset = getUtility(IPersonSet)
        person = personset.getByEmail(email)

        if person is None:
            # We create a new user without a password.
            comment = 'when importing the %s translation of %s' % (
                self.pofile.language.displayname, self.potemplate.displayname)

            person, dummy = personset.createPersonAndEmail(
                email, PersonCreationRationale.POFILEIMPORT, displayname=name,
                comment=comment)

        return person

    def import_file(self, translation_import_queue_entry, logger=None):
        """See ITranslationImporter."""
        assert translation_import_queue_entry is not None, (
            "The translation import queue entry cannot be None.")

        librarian_client = getUtility(ILibrarianClient)
        import_file = librarian_client.getFileByAlias(entry_to_import.content.id)

        if translation_import_queue_entry.lower().endswith('.xpi'):
            file = MozillaSupport(
                path=entry_to_import.path,
                productseries=entry_to_import.productseries,
                distrorelease=entry_to_import.distrorelease,
                sourcepackagename=entry_to_import.sourcepackagename,
                is_published=entry_to_import.is_published,
                content=import_file.read(),
                logger=logger)
            self.source_file = entry_to_import.content
            self.source_file_format = entry_to_import.format
        else:
            file = PoSupport(
                path=entry_to_import.path,
                productseries=entry_to_import.productseries,
                distrorelease=entry_to_import.distrorelease,
                sourcepackagename=entry_to_import.sourcepackagename,
                is_published=entry_to_import.is_published,
                content=import_file.read(),
                logger=logger)

        header = file['header']
        messages = file['messages']

        # This var will hold an special IPOFile for 'English' which will have
        # the English strings to show instead of arbitrary IDs.
        english_pofile = None
        if IPOFile.providedBy(pofile_or_potemplate):
            self.pofile = pofile_or_potemplate
            self.potemplate = self.pofile.potemplate
            # Check whether we are importing a new version.
            if header and self.pofile.isPORevisionDateOlder(header):
                # The new imported file is older than latest one imported, we
                # don't import it, just ignore it as it could be a mistake and
                # it would make us lose translations.
                raise OldTranslationImported(
                    'Previous imported file is newer than this one.')

            # Get the timestamp when this file was exported from Launchpad. If
            # it was not exported from Rosetta, it will be None.
            lock_timestamp = header.getRosettaExportDate()

            if not published and lock_timestamp is None:
                # We got a translation file from offline translation (not
                # published) and it misses the export time so we don't have a
                # way to figure whether someone changed the same translations
                # while the offline work was done.
                raise NotExportedFromLaunchpad

            # Expire old messages
            self.pofile.expireAllMessages()
            # Update the header with the new one.
            self.pofile.updateHeader(header)
            # Get last translator that touched this translation file.
            last_translator = self.getPersonByEmail(
                file['lasttranslatoremail'], file['lasttranslatorname'])

            if last_translator is None:
                # We were not able to guess it from the translation file, so
                # we take the importer as the last translator.
                last_translator = importer

        elif IPOTemplate.providedBy(pofile_or_potemplate):
            self.pofile = None
            self.potemplate = pofile_or_potemplate
            self.potemplate.source_file_format = file['format']
            # XXX: This should be done in a generic way so we handle this
            # automatically without knowing the exact formats that need it.
            if file['format'] == RosettaFileFormat.XPI:
                english_pofile = self.potemplate.getPOFileByLang('en')
                if english_pofile is None:
                    english_pofile = self.potemplate.newPOFile('en')
            # Expire old messages
            self.potemplate.expireAllMessages()
            if header is not None:
                # Update the header
                self.potemplate.header = header.msgstr
            UTC = pytz.timezone('UTC')
            potemplate.date_last_updated = datetime.datetime.now(UTC)
        else:
            raise TypeError(
                'Bad argument %s, an IPOTemplate or IPOFile was expected.' %
                    repr(pofile_or_potemplate))

        count = 0

        errors = []
        for pomsg in messages:
            if pomsg.get('msgid', None) is None:
                # The message has no msgid, we ignore it and jump to next
                # message.
                continue

            # Add the msgid.
            potmsgset = self.potemplate.getPOTMsgSetByMsgIDText(
                pomsg['msgid'])

            if potmsgset is None:
                # It's the first time we see this msgid, we need to create the
                # IPOTMsgSet for it.
                potmsgset = self.potemplate.createMessageSetFromText(
                    pomsg['msgid'])
            else:
                # Note that we saw it.
                potmsgset.makeMessageIDSighting(
                    pomsg['msgid'], TranslationConstants.SINGULAR_FORM,
                    update=True)

            # Add the English plural form.
            if pomsg.get('msgid_plural', None) is not None:
                # Check whether this message had already a plural form in its
                # previous import.
                if (potmsgset.msgid_plural is not None and
                    potmsgset.msgid_plural != pomsg['msgid_plural'] and
                    self.pofile is not None):
                    # The PO file wants to change the msgidPlural from the PO
                    # template, that's broken and not usual, so we raise an
                    # exception to log the issue. It needs to be fixed
                    # manually in the imported translation file.
                    # XXX CarlosPerelloMarin 20070423: Gettext doesn't allow
                    # two plural messages with the same msgid but different
                    # msgid_plural so I think is safe enough to just go ahead
                    # and import this translation here but setting the fuzzy
                    # flag. See bug #109393 for more info.
                    pomsgset = potmsgset.getPOMsgSet(
                        self.pofile.language.code, self.pofile.variant)
                    if pomsgset is None:
                        pomsgset = (
                            self.pofile.createMessageSetFromMessageSet(
                                potmsgset))
                    # Add the pomsgset to the list of pomsgsets with errors.
                    error = {
                        'pomsgset': pomsgset,
                        'pomessage': pomsg,
                        'error-message': (
                            "The msgid_plural field has changed since last"
                            " time this file was\ngenerated, please report"
                            " this error to %s" % (
                                config.rosetta.rosettaadmin.email))
                    }

                    errors.append(error)
                    continue

                # Note that we saw this plural form.
                potmsgset.makeMessageIDSighting(
                    pomsg['msgid_plural'], TranslationConstants.PLURAL_FORM,
                    update=True)

            # Update the position
            count += 1

            for commentfield in ['comment', 'sourcecomment', 'filerefs']:
                if pomsg[commentfield] is not None:
                    pomsg[commentfield] = pomsg[commentfield].rstrip()

            commenttext = pomsg['comment']
            sourcecomment = pomsg['sourcecomment']
            filereferences = pomsg['filerefs']

            if 'fuzzy' in pomsg['flags']:
                pomsg['flags'].remove('fuzzy')
                fuzzy = True
                flagscomment = u", fuzzy"
            else:
                fuzzy = False
                flagscomment = u""
            flagscomment += u", ".join(pomsg['flags'])

            if self.pofile is None:
                # The import is a translation template file
                potmsgset.sequence = count
                potmsgset.commenttext = commenttext
                potmsgset.sourcecomment = sourcecomment
                potmsgset.filereferences = filereferences
                potmsgset.flagscomment = flagscomment

                # Finally, we need to invalidate the cached translation file
                # exports so new downloads get the new messages from this
                # import.
                self.potemplate.invalidateCache()

                if english_pofile is not None:
                    # The English strings for this template are stored inside
                    # an IPOFile.
                    pomsgset = potmsgset.getPOMsgSet(
                        english_pofile.language.code)
                    if pomsgset is None:
                        # There is no such pomsgset, we need to create it.
                        pomsgset = (
                            english_pofile.createMessageSetFromMessageSet(
                                potmsgset)

                    pomsgset.sequence = count

                # By default translation template uploads are done only by
                # editors.
                is_editor = True
                last_translator = importer
                lock_timestamp = None
            else:
                # The import is a translation file.
                pomsgset = potmsgset.getPOMsgSet(
                    self.pofile.language.code, self.pofile.variant)
                if pomsgset is None:
                    # There is no such pomsgset.
                    pomsgset = self.pofile.createMessageSetFromMessageSet(
                        potmsgset)

                pomsgset.sequence = count
                pomsgset.commenttext = commenttext
                if potmsgset.sequence == 0:
                    # We are importing a message that does not exists in
                    # latest translation template so we can update its values.
                    potmsgset.sourcecomment = sourcecomment
                    potmsgset.filereferences = filereferences
                    pomsgset.flagscomment = flagscomment

                pomsgset.obsolete = pomsg['obsolete']

                # Use the importer rights to make sure the imported
                # translations are actually accepted instead of being just
                # suggestions.
                is_editor = self.pofile.canEditTranslations(importer)

            # Store translations
            if self.pofile is None and english_pofile is None:
                # It's neither an IPOFile nor an IPOTemplate that needs to
                # store English strings in an IPOFile.
                continue

            translations = pomsg['msgstr']
            if not translations:
                # We don't have anything to import.
                continue

            try:
                pomsgset.updateTranslationSet(
                    last_translator, translations, fuzzy, published,
                    lock_timestamp, force_edition_rights=is_editor)
            except TranslationConflict:
                error = {
                    'pomsgset': pomsgset,
                    'pomessage': pomessage,
                    'error-message': (
                        "This message was updated by someone else after you"
                        " got the translation file.\n This translation is now"
                        " stored as a suggestion, if you want to set it\n as"
                        " the used one, go to\n %s/+translate\n and approve"
                        " it." % canonical_url(pomsgset))
                }

                errors.append(error)
            except gettextpo.error, e:
                # We got an error, so we submit the translation again but
                # this time asking to store it as a translation with
                # errors.
                pomsgset.updateTranslationSet(
                    last_translator, translations, fuzzy, published,
                    lock_timestamp, ignore_errors=True,
                    force_edition_rights=is_editor)

                # Add the pomsgset to the list of pomsgsets with errors.
                error = {
                    'pomsgset': pomsgset,
                    'pomessage': pomsg,
                    'error-message': e
                }

                errors.append(error)

        return errors

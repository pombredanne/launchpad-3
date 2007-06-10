# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TranslationImporter',
    ]

import gettextpo
import datetime
import pytz
from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.launchpad.components.translationformats.gettext_po_importer import (
    TranslationFormatImporter as GettextPoImporter)
from canonical.launchpad.interfaces import (
        IPersonSet, ITranslationImporter, TranslationConstants,
        TranslationConflict, OldTranslationImported, NotExportedFromLaunchpad)
from canonical.launchpad.webapp import canonical_url
from canonical.lp.dbschema import (
    TranslationFileFormat, RosettaImportStatus, PersonCreationRationale)

# Registered importers.
importers = {
    TranslationFileFormat.PO: GettextPoImporter,
    }


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

    def getImporterByFileFormat(self, file_format):
        """Return an ITranslationFormatImporter that handles given file format.

        Return None if there is no importer to handle it.
        """
        return importers.get(file_format, None)

    def import_file(self, translation_import_queue_entry, logger=None):
        """See ITranslationImporter."""
        assert translation_import_queue_entry is not None, (
            "The translation import queue entry cannot be None.")
        assert (translation_import_queue_entry.status ==
                RosettaImportStatus.APPROVED), (
                "The entry is not approved!.")
        assert (translation_import_queue_entry.potemplate is not None or
                translation_import_queue_entry.pofile is not None), (
                "The entry has not any import target.")

        importer_class = self.getImporterByFileFormat(
            translation_import_queue_entry.format)
        assert importer_class is not None, (
            'There is no importer available for %s files' % (
                translation_import_queue_entry.format.name))

        importer = importer_class(translation_import_queue_entry, logger=logger)

        self.pofile = translation_import_queue_entry.pofile
        if translation_import_queue_entry.pofile is None:
            self.potemplate = translation_import_queue_entry.potemplate
        else:
            self.potemplate = self.pofile.potemplate

        if self.pofile is None:
            # We are importing a translation template.
            self.potemplate.source_file_format = (
                translation_import_queue_entry.format)
            # Expire old messages
            self.potemplate.expireAllMessages()
            if importer.header is not None:
                # Update the header
                self.potemplate.header = importer.header.getRawContent()
            UTC = pytz.timezone('UTC')
            self.potemplate.date_last_updated = datetime.datetime.now(UTC)
        else:
            # We are importing a translation.
            # Check whether we are importing a new version.
            if (importer.header is not None and
                self.pofile.isPORevisionDateOlder(importer.header)):
                # The new imported file is older than latest one imported, we
                # don't import it, just ignore it as it could be a mistake and
                # it would make us lose translations.
                raise OldTranslationImported(
                    'Previous imported file is newer than this one.')

            # Get the timestamp when this file was exported from Launchpad. If
            # it was not exported from Launchpad, it will be None.
            lock_timestamp = importer.header.getLaunchpadExportDate()

            if (not translation_import_queue_entry.is_published and
                lock_timestamp is None):
                # We got a translation file from offline translation (not
                # published) and it misses the export time so we don't have a
                # way to figure whether someone changed the same translations
                # while the offline work was done.
                raise NotExportedFromLaunchpad

            # Expire old messages
            self.pofile.expireAllMessages()
            # Update the header with the new one.
            self.pofile.updateHeader(importer.header)
            # Get last translator that touched this translation file.
            name, email = importer.getLastTranslator()
            last_translator = self.getPersonByEmail(email, name)

            if last_translator is None:
                # We were not able to guess it from the translation file, so
                # we take the importer as the last translator.
                last_translator = translation_import_queue_entry.importer

        count = 0

        errors = []
        for message in importer.messages:
            if not message.msgid:
                # The message has no msgid, we ignore it and jump to next
                # message.
                continue

            # Add the msgid.
            potmsgset = self.potemplate.getPOTMsgSetByMsgIDText(message.msgid)

            if potmsgset is None:
                # It's the first time we see this msgid, we need to create the
                # IPOTMsgSet for it.
                potmsgset = self.potemplate.createMessageSetFromText(
                    message.msgid)
            else:
                # Note that we saw it.
                potmsgset.makeMessageIDSighting(
                    message.msgid, TranslationConstants.SINGULAR_FORM,
                    update=True)

            # Add the English plural form.
            if message.msgid_plural:
                # Check whether this message had already a plural form in its
                # previous import.
                if (potmsgset.msgid_plural is not None and
                    potmsgset.msgid_plural != message.msgid_plural and
                    self.pofile is not None):
                    # The PO file wants to change the plural msgid from the PO
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
                        'pomessage': unicode(message),
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
                    message.msgid_plural, TranslationConstants.PLURAL_FORM,
                    update=True)

            # Update the position
            count += 1

            if 'fuzzy' in message.flags:
                message.flags.remove('fuzzy')
                fuzzy = True
                flags_comment = u", fuzzy"
            else:
                fuzzy = False
                flags_comment = u""
            flags_comment += u", ".join(message.flags)

            if self.pofile is None:
                # The import is a translation template file
                potmsgset.sequence = count
                potmsgset.commenttext = message.comment
                potmsgset.sourcecomment = message.source_comment
                potmsgset.filereferences = message.file_references
                potmsgset.flagscomment = flags_comment

                # Finally, we need to invalidate the cached translation file
                # exports so new downloads get the new messages from this
                # import.
                self.potemplate.invalidateCache()

                # By default translation template uploads are done only by
                # editors.
                is_editor = True
                last_translator = translation_import_queue_entry.importer
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
                pomsgset.commenttext = message.comment
                if potmsgset.sequence == 0:
                    # We are importing a message that does not exists in
                    # latest translation template so we can update its values.
                    potmsgset.sourcecomment = message.source_comment
                    potmsgset.filereferences = message.file_references
                    pomsgset.flagscomment = flags_comment

                pomsgset.obsolete = message.obsolete

                # Use the importer rights to make sure the imported
                # translations are actually accepted instead of being just
                # suggestions.
                is_editor = self.pofile.canEditTranslations(
                    translation_import_queue_entry.importer)

            # Store translations
            if self.pofile is None:
                # It's not an IPOFile.
                continue

            if not message.translations:
                # We don't have anything to import.
                continue

            translations = {}
            for index in range(len(message.translations)):
                translations[index] = message.translations[index]

            try:
                pomsgset.updateTranslationSet(
                    last_translator, translations, fuzzy,
                    translation_import_queue_entry.is_published, lock_timestamp,
                    force_edition_rights=is_editor)
            except TranslationConflict:
                error = {
                    'pomsgset': pomsgset,
                    'pomessage': unicode(message),
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
                    last_translator, translations, fuzzy,
                    translation_import_queue_entry.is_published, lock_timestamp,
                    ignore_errors=True, force_edition_rights=is_editor)

                # Add the pomsgset to the list of pomsgsets with errors.
                error = {
                    'pomsgset': pomsgset,
                    'pomessage': unicode(message),
                    'error-message': unicode(e)
                }

                errors.append(error)

        return errors

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

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.interfaces import (
    IPersonSet, ITranslationExporter, ITranslationImporter,
    NotExportedFromLaunchpad, OutdatedTranslationError,
    PersonCreationRationale, TranslationConflict, TranslationConstants)
from canonical.launchpad.translationformat.gettext_po_importer import (
    GettextPOImporter)
from canonical.launchpad.translationformat.mozilla_xpi_importer import (
    MozillaXpiImporter)
from canonical.launchpad.webapp import canonical_url
from canonical.lp.dbschema import (
    RosettaImportStatus, TranslationFileFormat)

importers = {
    TranslationFileFormat.PO: GettextPOImporter(),
    TranslationFileFormat.XPI: MozillaXpiImporter(),
    }

class TranslationImporter:
    """Handle translation resources imports."""

    implements(ITranslationImporter)

    def __init__(self):
        self.pofile = None
        self.potemplate = None

    def _getPersonByEmail(self, email, name=None):
        """Return the person for given email.

        :param email: text that contains the email address.
        :param name: name of the owner of the given email address.

        If email is None, return None.
        If the person is unknown in Launchpad, the account will be created but
        it will not have a password and thus, will be disabled.
        """
        assert self.pofile is not None, 'self.pofile cannot be None'

        if email is None:
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

    @cachedproperty
    def supported_file_extensions(self):
        """See ITranslationImporter."""
        file_extensions = []

        for importer in importers.itervalues():
            file_extensions.extend(importer.file_extensions)

        return sorted(file_extensions)

    def getTranslationFileFormatByFileExtension(self, file_extension):
        """See `ITranslationImporter`."""
        for importer in importers.itervalues():
            if file_extension in importer.file_extensions:
                return importer.format

        return None

    def getTranslationFormatImporter(self, file_format):
        """See `ITranslationImporter`."""
        return importers.get(file_format, None)

    def importFile(self, translation_import_queue_entry, logger=None):
        """See ITranslationImporter."""
        assert translation_import_queue_entry is not None, (
            "The translation import queue entry cannot be None.")
        assert (translation_import_queue_entry.status ==
                RosettaImportStatus.APPROVED), (
                "The entry is not approved!.")
        assert (translation_import_queue_entry.potemplate is not None or
                translation_import_queue_entry.pofile is not None), (
                "The entry has not any import target.")

        importer = self.getTranslationFormatImporter(
            translation_import_queue_entry.format)
        exporter = getUtility(ITranslationExporter)
        format_exporter = exporter.getExporterProducingTargetFileFormat(
            importer.format)

        assert importer is not None, (
            'There is no importer available for %s files' % (
                translation_import_queue_entry.format.name))

        translation_file = importer.parse(translation_import_queue_entry)

        # This var will hold an special IPOFile for 'English' which will have
        # the English strings to show instead of arbitrary IDs.
        english_pofile = None
        self.pofile = translation_import_queue_entry.pofile
        lock_timestamp = None
        if translation_import_queue_entry.pofile is None:
            self.potemplate = translation_import_queue_entry.potemplate
        else:
            self.potemplate = self.pofile.potemplate

        if self.pofile is None:
            # We are importing a translation template.
            self.potemplate.source_file_format = (
                translation_import_queue_entry.format)
            if importer.uses_source_string_msgids:
                # We use the special 'en' language as the way to store the
                # English strings to show instead of the msgids.
                english_pofile = self.potemplate.getPOFileByLang('en')
                if english_pofile is None:
                    english_pofile = self.potemplate.newPOFile('en')
            # Expire old messages
            self.potemplate.expireAllMessages()
            if translation_file.header is not None:
                # Update the header
                self.potemplate.header = (
                    translation_file.header.getRawContent())
            UTC = pytz.timezone('UTC')
            self.potemplate.date_last_updated = datetime.datetime.now(UTC)
        else:
            # We are importing a translation.
            if translation_file.header is not None:
                # Check whether we are importing a new version.
                if self.pofile.isTranslationRevisionDateOlder(
                    translation_file.header):
                    # The new imported file is older than latest one imported,
                    # we don't import it, just ignore it as it could be a
                    # mistake and it would make us lose translations.
                    raise OutdatedTranslationError(
                        'Previous imported file is newer than this one.')
                # Get the timestamp when this file was exported from
                # Launchpad. If it was not exported from Launchpad, it will be
                # None.
                lock_timestamp = translation_file.header.launchpad_export_date

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
            self.pofile.updateHeader(translation_file.header)
            # Get last translator that touched this translation file.
            name, email = translation_file.header.getLastTranslator()
            last_translator = self._getPersonByEmail(email, name)

            if last_translator is None:
                # We were not able to guess it from the translation file, so
                # we take the importer as the last translator.
                last_translator = translation_import_queue_entry.importer

        count = 0

        errors = []
        for message in translation_file.messages:
            if not message.msgid:
                # The message has no msgid, we ignore it and jump to next
                # message.
                continue

            # Add the msgid.
            potmsgset = self.potemplate.getPOTMsgSetByMsgIDText(
                message.msgid, context=message.context)

            if potmsgset is None:
                # It's the first time we see this msgid, we need to create the
                # IPOTMsgSet for it.
                potmsgset = self.potemplate.createMessageSetFromText(
                    message.msgid, context=message.context)
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
                    # XXX CarlosPerelloMarin 2007-04-23 bug=109393:
                    # Gettext doesn't allow two plural messages with the
                    # same msgid but different msgid_plural so I think is
                    # safe enough to just go ahead and import this translation
                    # here but setting the fuzzy flag.
                    pomsgset = potmsgset.getPOMsgSet(
                        self.pofile.language.code, self.pofile.variant)
                    if pomsgset is None:
                        pomsgset = (
                            self.pofile.createMessageSetFromMessageSet(
                                potmsgset))

                    # Add the pomsgset to the list of pomsgsets with errors.
                    error = {
                        'pomsgset': pomsgset,
                        'pomessage': format_exporter.exportTranslationMessage(
                            message),
                        'error-message': (
                            "The msgid_plural field has changed since the"
                            " last time this file was generated, please"
                            " report this error to %s" % (
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

                if english_pofile is not None:
                    # The English strings for this template are stored inside
                    # an IPOFile.
                    pomsgset = potmsgset.getPOMsgSet(
                        english_pofile.language.code)
                    if pomsgset is None:
                        # There is no such pomsgset, we need to create it.
                        pomsgset = (
                            english_pofile.createMessageSetFromMessageSet(
                                potmsgset))

                    pomsgset.sequence = count

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

                pomsgset.obsolete = message.is_obsolete

                # Use the importer rights to make sure the imported
                # translations are actually accepted instead of being just
                # suggestions.
                is_editor = self.pofile.canEditTranslations(
                    translation_import_queue_entry.importer)

            # Store translations
            if self.pofile is None and english_pofile is None:
                # It's neither an IPOFile nor an IPOTemplate that needs to
                # store English strings in an IPOFile.
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
                    translation_import_queue_entry.is_published,
                    lock_timestamp, force_edition_rights=is_editor)
            except TranslationConflict:
                error = {
                    'pomsgset': pomsgset,
                    'pomessage': format_exporter.exportTranslationMessage(
                        message),
                    'error-message': (
                        "This message was updated by someone else after you"
                        " got the translation file. This translation is now"
                        " stored as a suggestion, if you want to set it as"
                        " the used one, go to %s/+translate and approve"
                        " it." % canonical_url(pomsgset))
                }

                errors.append(error)
            except gettextpo.error, e:
                # We got an error, so we submit the translation again but
                # this time asking to store it as a translation with
                # errors.
                pomsgset.updateTranslationSet(
                    last_translator, translations, fuzzy,
                    translation_import_queue_entry.is_published,
                    lock_timestamp, ignore_errors=True,
                    force_edition_rights=is_editor)

                # Add the pomsgset to the list of pomsgsets with errors.
                error = {
                    'pomsgset': pomsgset,
                    'pomessage': format_exporter.exportTranslationMessage(
                        message),
                    'error-message': unicode(e)
                }

                errors.append(error)

        return errors

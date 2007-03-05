# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import gettextpo
import datetime
import pytz
from email.Utils import parseaddr
from zope.component import getUtility
from sqlobject import SQLObjectNotFound
#from canonical.launchpad.database.pomsgid import POMsgID

from canonical.config import config
from canonical.launchpad.interfaces import (
        IPOTemplate, IPOFile, IPersonSet, TranslationConstants,
        TranslationConflict)
from canonical.launchpad.components.poparser import POParser
from canonical.lp.dbschema import PersonCreationRationale
from canonical.launchpad.webapp import canonical_url

class OldPOImported(Exception):
    """Raised when an older PO file is imported."""

class NotExportedFromRosetta(Exception):
    """Raised when a PO file imported lacks the export time from Rosetta."""

def getPersonByEmail(pofile, email, name=None):
    """Return the person for given email.

    If the person is unknown in launchpad, the account will be created.
    """
    if not email or email == 'EMAIL@ADDRESS' or not '@' in email:
        return None
    else:
        personset = getUtility(IPersonSet)
        person = personset.getByEmail(email)

        if person is None:
            # We create a new user without a password.
            comment = ('when importing the %s translation of %s'
                       % (pofile.language.displayname,
                          pofile.potemplate.displayname))
            person, dummy = personset.createPersonAndEmail(
                email, PersonCreationRationale.POFILEIMPORT,
                displayname=name, comment=comment)

        return person

def translation_import(pofile_or_potemplate, file, importer, published=True):
    """Convert a .pot or .po file into DB objects.

    :arg pofile_or_potemplate: is the IPOFile or IPOTemplate object where the
        import will be done.
    :arg file: is dict containing header and messages we are importing.
    :arg importer: is the person who requested this import.
    :arg published: indicates if the file being imported is published or just a
        translation update. With template files should be always published.

    If file is older than previous imported file, OldPOImported exception is
    raised.

    Return a list of dictionaries with three keys:
        - 'pomsgset': The DB pomsgset with an error.
        - 'pomessage': The original POMessage object.
        - 'error-message': The error message as gettext names it.
    """
    assert importer is not None, "The importer cannot be None."

    header = file['header']
    messages = file['messages']

    if IPOFile.providedBy(pofile_or_potemplate):
        pofile = pofile_or_potemplate
        potemplate = pofile.potemplate
        # Check if we are importing a new version.
        if header and pofile.isPORevisionDateOlder(header):
            # The new imported file is older than latest one imported, we
            # don't import it, just ignore it as it could be a mistake and
            # would make us lose translations.
            raise OldPOImported(
                'Previous imported file is newer than this one.')
        else:
            lock_timestamp = header.getRosettaExportDate()

            if not published and lock_timestamp is None:
                # We got a .po file from offline translation (not published)
                # and it misses the export time.
                raise NotExportedFromRosetta

            # Expire old messages
            pofile.expireAllMessages()
            # Update the header
            pofile.updateHeader(header)
            # Get last translator.
            last_translator = getPersonByEmail(pofile,
                                               file['lasttranslatoremail'],
                                               file['lasttranslatorname'])
            if last_translator is None:
                # We were not able to guess it from the .po file, so we take
                # the importer as the last translator.
                last_translator = importer

    elif IPOTemplate.providedBy(pofile_or_potemplate):
        pofile = None
        potemplate = pofile_or_potemplate
        # Expire old messages
        potemplate.expireAllMessages()
        if header is not None:
            # Update the header
            potemplate.header = header.msgstr
        UTC = pytz.timezone('UTC')
        potemplate.date_last_updated = datetime.datetime.now(UTC)
    else:
        raise TypeError(
            'Bad argument %s, an IPOTemplate or IPOFile was expected.' %
                repr(pofile_or_potemplate))

    count = 0

    errors = []
    import sys
    for pomsg in messages:
        # Add the msgid.
        potmsgset = potemplate.getPOTMsgSetByMsgIDText(pomsg['msgid'])

        if potmsgset is None:
            # It's the first time we see this msgid.
            if not pomsg['msgid']:
                continue
            potmsgset = potemplate.createMessageSetFromText(pomsg['msgid'])
        else:
            # XXX: set fuzzy marker if primemsgid actually changes
            # Note that we saw it.
            if pomsg['msgid']:
#                 if pomsg['msgid'] != potmsgset.primemsgid_.msgid:
#                     try:
#                         messageID = POMsgID.byMsgid(pomsg['msgid'])
#                     except SQLObjectNotFound:
#                         # If there are no existing message ids,
#                         # create a new one.
#                         messageID = POMsgID(msgid=text)
#                     potmsgset.primemsgid_ = messageID
#                     if not 'fuzzy' in pomsg['flags']:
#                         pomsg['flags'].append('fuzzy')

                potmsgset.makeMessageIDSighting(
                    pomsg['msgid'], TranslationConstants.SINGULAR_FORM,
                    update=True)

        # Add the English plural form.
        if pomsg['msgid_plural']:
            # Check if old potmsgset had a plural form already and mark as not
            # available in the file being imported.
            if potmsgset.msgid_plural is not None:
                if (potmsgset.msgid_plural != pomsg['msgid_plural'] and
                    pofile is not None):
                    # The PO file wants to change the msgidPlural from the PO
                    # template, that's broken and not usual, so we raise an
                    # exception to log the issue and fix it manually.
                    pomsgset = potmsgset.getPOMsgSet(
                        pofile.language.code, pofile.variant)
                    if pomsgset is None:
                        pomsgset = pofile.createMessageSetFromMessageSet(potmsgset)
                    # Add the pomsgset to the list of pomsgsets with errors.
                    error = {
                        'pomsgset': pomsgset,
                        'pomessage': pomsg,
                        'error-message': ("The msgid_plural field has changed"
                            " since last time this .po file was\ngenerated,"
                            " please report this error to %s" %
                                          config.rosetta.rosettaadmin.email)
                    }

                    errors.append(error)
                    continue

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

        if pofile is None:
            # The import is a .pot file
            potmsgset.sequence = count
            potmsgset.commenttext = commenttext
            potmsgset.sourcecomment = sourcecomment
            potmsgset.filereferences = filereferences
            potmsgset.flagscomment = flagscomment

            # Finally, we need to invalidate the cached .po files so new
            # downloads get the new messages from this import.
            potemplate.invalidateCache()
        else:
            # The import is a .po file
            pomsgset = potmsgset.getPOMsgSet(
                pofile.language.code, pofile.variant)
            if pomsgset is None:
                # There is no such pomsgset.
                pomsgset = pofile.createMessageSetFromMessageSet(potmsgset)

            pomsgset.sequence = count
            pomsgset.commenttext = commenttext
            if potmsgset.sequence == 0:
                # We are importing a message that does not exists in latest
                # template so we can update the template values.
                potmsgset.sourcecomment = sourcecomment
                potmsgset.filereferences = filereferences
                pomsgset.flagscomment = flagscomment

            pomsgset.obsolete = pomsg['obsolete']

            # Store translations
            translations = pomsg['msgstr']
            if not translations:
                # We don't have anything to import.
                continue

            # Use the importer (rosetta-admins) rights to make sure the
            # imported translations are actually accepted instead of being 
            # just suggestions.
            is_editor = pofile.canEditTranslations(importer)
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
                        " got the .po file.\n This translation is now stored"
                        " as a suggestion, if you want to set it\n as the"
                        " used one, go to\n %s/+translate\n and"
                        " approve it." % canonical_url(pomsgset))
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

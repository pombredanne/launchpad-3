# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

#import gettextpo
import datetime
import pytz
from StringIO import StringIO
#from email.Utils import parseaddr
from zope.component import getUtility

from canonical.launchpad.interfaces import (
        IPOTemplate, IPOFile, IPersonSet, NotFoundError
        )
from canonical.launchpad.components.translation_importers import MozillaZipFile
from canonical.launchpad.helpers import TranslationConstants

class OldXPIImported(Exception):
    """Raised when an older XPI file is imported."""


def import_xpi(pofile_or_potemplate, file, importer, published=True):
    """Convert a .xpi file into DB objects.

    :arg pofile_or_potemplate: is the IPOFile or IPOTemplate object where the
        import will be done.
    :arg file: is a file-like object with the content we are importing.
    :arg importer: is the person who requested this import.
    :arg published: indicates if the file being imported is published or just a
        translation update. With template files should be always published.

    If file is older than previous imported file, OldXPIImported exception is
    raised.

    Return a list of dictionaries with three keys:
        - 'pomsgset': The DB pomsgset with an error.
        - 'pomessage': The original POMessage object.
        - 'error-message': The error message as gettext names it.
    """
    assert importer is not None, "The importer cannot be None."

    messages = MozillaZipFile(StringIO(file.read()))

    if IPOFile.providedBy(pofile_or_potemplate):
        pofile = pofile_or_potemplate
        potemplate = pofile.potemplate
        # Check if we are importing a new version.
        #if pofile.isPORevisionDateOlder(parser.header):
        #    # The new imported file is older than latest one imported, we
        #    # don't import it, just ignore it as it could be a mistake and
        #    # would make us lose translations.
        #    raise OldXPIImported(
        #        'Previous imported file is newer than this one.')
        #else:
        # Expire old messages
        pofile.expireAllMessages()
        # Update the header
        #pofile.updateHeader(parser.header)
        # Get last translator.
        last_translator = messages.getLastTranslator()
        if last_translator is None:
            # We were not able to guess it from the .po file, so we take
            # the importer as the last translator.
            last_translator = importer
        is_editor = pofile.canEditTranslations(importer)
    elif IPOTemplate.providedBy(pofile_or_potemplate):
        pofile = None
        potemplate = pofile_or_potemplate
        # Expire old messages
        potemplate.expireAllMessages()
        #if messages.header is not None:
        #    # Update the header
        #    potemplate.header = messages.header
        UTC = pytz.timezone('UTC')
        potemplate.date_last_updated = datetime.datetime.now(UTC)
    else:
        raise TypeError(
            'Bad argument %s, an IPOTemplate or IPOFile was expected.' %
                repr(pofile_or_potemplate))

    count = 0

    errors = []
    for alt_msgid in messages:
        # Add the English msgid.
        try:
            pomsgid = messages[alt_msgid]['content']
            potmsgset = potemplate.getPOTMsgSetByMsgIDText(pomsgid)
            potmsgset.makeMessageIDSighting(
                pomsgid, TranslationConstants.SINGULAR_FORM,
                update=True)
        except NotFoundError:
            # It's the first time we see this msgid.
            potmsgset = potemplate.createMessageSetFromText(pomsgid, alt_msgid)

        # Update the position
        count += 1

        commenttext = None
        fuzzy = False
        flagscomment = None

        sourcecomment = '\n'.join(messages[alt_msgid]['comments'])
        if sourcecomment is not None:
            sourcecomment = sourcecomment.rstrip()

        filereferences = ' '.join(messages[alt_msgid]['sourcerefs'])
        if filereferences is not None:
            filereferences = filereferences.rstrip()


        if pofile is None:
            # The import is an en-US.xpi file
            potmsgset.sequence = count
            potmsgset.commenttext = commenttext
            potmsgset.sourcecomment = sourcecomment
            potmsgset.filereferences = filereferences
            potmsgset.flagscomment = flagscomment

            # Finally, we need to invalidate the cached .po files so new
            # downloads get the new messages from this import.
            potemplate.invalidateCache()
        else:
            # The import is another language .xpi file
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

            pomsgset.obsolete = False

            # Store translations
#             if pomessage.msgstr is not None:
#                 translations = { 0: pomessage.msgstr }
#             else:
#                 # We don't have anything to import.
#                 continue

#             try:
#                 pomsgset.updateTranslationSet(last_translator,
#                                               translations,
#                                               fuzzy, published,
#                                               force_edition_rights=is_editor)
#             except gettextpo.error, e:
#                 # We got an error, so we submit the translation again but
#                 # this time asking to store it as a translation with
#                 # errors.
#                 pomsgset.updateTranslationSet(last_translator,
#                                               translations,
#                                               fuzzy, published,
#                                               ignore_errors=True,
#                                               force_edition_rights=is_editor)

#                 # Add the pomsgset to the list of pomsgsets with errors.
#                 error = {
#                     'pomsgset': pomsgset,
#                     'pomessage': pomessage,
#                     'error-message': e
#                 }

#                 errors.append(error)

    return errors

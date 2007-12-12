# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper module reused in different tests."""

__metaclass__ = type

__all__ = [
    'import_pofile_or_potemplate',
    'is_valid_mofile',
    ]

import transaction

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ITranslationImportQueue, RosettaImportStatus)
from canonical.launchpad.scripts import FakeLogger


def import_pofile_or_potemplate(file_contents, person, series, pofile=None,
    potemplate=None, is_imported=True):
    """Import a `POFile` or `POTemplate` from the given string.

    :param file_contents: text of "file" to import.
    :param person: party requesting the import.
    :param series: product series the import is for.
    :param pofile: if uploading a `POFile`, file to import to; None otherwise.
    :param potemplate: if uploading a `POTemplate`, file to import to; None
        otherwise.
    :return: `TranslationImportQueueEntry` as added to the import queue.
    """
    translation_import_queue = getUtility(ITranslationImportQueue)
    if pofile is not None:
        entry = translation_import_queue.addOrUpdateEntry(
            pofile.path, file_contents, is_imported, person,
            productseries=series, pofile=pofile)
        target = pofile
    else:
        # A POTemplate can only be 'imported', so setting the is_imported flag
        # makes no difference.
        entry = translation_import_queue.addOrUpdateEntry(
            potemplate.path, file_contents, True, person,
            productseries=series, potemplate=potemplate)
        target = potemplate
    # Allow Librarian to see the change.
    transaction.commit()
    entry.status = RosettaImportStatus.APPROVED
    (subject, body) = target.importFromQueue(entry, FakeLogger())
    return entry


def is_valid_mofile(mofile):
    """Test whether a string is a valid MO file."""
    # There are different magics for big- and little-endianness, so we
    # test for both.
    be_magic = '\x95\x04\x12\xde'
    le_magic = '\xde\x12\x04\x95'

    return mofile[:len(be_magic)] in (be_magic, le_magic)

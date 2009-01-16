from datetime import timedelta, utcnow

import gettextpo

from canonical.launchpad.helpers import validate_translation


def log_bad_message(translationmessage, error):
    """Report gettext validation error for active message."""


def log_bad_imported_message(translationmessage):
    """Report that translationmessage is imported and broken.

    This probably means a problem in the upstream translation.
    """


def check_message(translationmessage):
    """Check if this message looks valid to gettext.

    :return: True if message is OK, False otherwise.
    """
    potmsgset = translationmessage.potmsgset
    msgids = potmsgset._list_of_msgids()
    msgstrs = translationmessage.translations

    try:
        helpers.validate_translation(msgids, msgstrs, potmsgset.flags)
    except gettextpo.error error:
        log_bad_message(translationmessage, error.represent())
        return False
    return True


def get_imported_alternative(translationmessage):
    if translationmessage.is_imported:
        return None

    potmsgset = translationmessage.potmsgset
    pofile = translationmessage.pofile
    return potmsgset.getImportedTranslationMessage(
        pofile.language, pofile.variant)


def check_and_fix(translationmessage):
    if check_message(translationmessage):
        return

    translationmessage.is_current = False

    imported = get_imported_alternative(translationmessage)
    if imported is not None and check_message(imported):
        imported.is_current = True


def iterate(messages, transactionmanager):
    """Go over `messages`; check and fix them, committing regularly,"""
    commit_interval = timedelta(0, 3)
    next_commit = utcnow() + commit_interval
    for message in messages:
        check_and_fix(message)
        if utcnow() >= next_commit:
            transactionmanager.commit()
            transactionmanager.begin()
            next_commit = utcnow() + commit_interval


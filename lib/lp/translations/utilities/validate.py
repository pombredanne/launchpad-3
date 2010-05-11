# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'GettextValidationError',
    'validate_translation',
    ]

import gettextpo


class GettextValidationError(ValueError):
    """Gettext validation failed."""


def validate_translation(original, translation, flags):
    """Check with gettext if a translation is correct or not.

    If the translation has a problem, raise `GettextValidationError`.

    :param msgids: A list of one or two msgids, depending on whether the
        message has a plural.
    :param translation: A dictionary of translations, indexed with the plural
        form number.
    :param flags: This message's flags as a list of strings.
    """
    msg = gettextpo.PoMessage()
    msg.set_msgid(original[0])

    if len(original) > 1:
        # It has plural forms.
        msg.set_msgid_plural(original[1])
        for form in range(len(translation)):
            msg.set_msgstr_plural(form, translation[form])
    elif len(translation) > 0:
        msg.set_msgstr(translation[0])
    else:
        pass

    for flag in flags:
        msg.set_format(flag, True)

    # Check the msg.
    try:
        msg.check_format()
    except gettextpo.error, e:
        # Wrap gettextpo.error in GettextValidationError.
        raise GettextValidationError(unicode(e))


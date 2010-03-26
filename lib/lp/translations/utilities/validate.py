# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import gettextpo


class GettextValidationError(ValueError):
    """Gettext validation failed."""

    def __init__(self, message_or_exception):
        """Extract message from gettextpo.error if if requested."""
        super(GettextValidationError, self).__init__(
            unicode(message_or_exception)) 


def validate_translation(original, translation, flags):
    """Check with gettext if a translation is correct or not.

    If the translation has a problem, raise gettextpo.error.
    """
    msg = gettextpo.PoMessage()
    msg.set_msgid(original[0])

    if len(original) > 1:
        # It has plural forms.
        msg.set_msgid_plural(original[1])
        for form in range(len(translation)):
            msg.set_msgstr_plural(form, translation[form])
    elif len(translation):
        msg.set_msgstr(translation[0])

    for flag in flags:
        msg.set_format(flag, True)

    # Check the msg.
    msg.check_format()


def validate_translations(msgids, translations, flags, ignore_errors=False):
    """Validate all the `translations`.

    :param msgids: A list of one or two msgids, depending on whether the
        message has a plural.
    :param translation: A dictionary of translations, indexed with the plural
        form number.
    :param flags: This message's flags as a list of strings.
    :param ignore_errors: Set to true to suppress exceptions from propagating.
    :return: True if the translations could be validated.
    """
    validated = True
    # Validate the translation we got from the translation form
    # to know if gettext is unhappy with the input.
    try:
        validate_translation(msgids, translations, flags)
    except gettextpo.error, e:
        if ignore_errors:
            # The translations are stored anyway, although they have not been
            # validated.status
            validated = False
        else:
            # Check to know if there is any translation.
            if any(translations.values()):
                # Partial translations cannot be stored, the
                # exception is raised again and handled outside
                # this method.
                raise GettextValidationError(e)

    return validated


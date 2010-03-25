# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import gettextpo


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


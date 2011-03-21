# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )


__metaclass__ = type

__all__ = [
    'TranslationConstants',
    'TranslationsBranchImportMode',
    ]



class TranslationConstants:
    """Set of constants used inside the context of translations."""

    SINGULAR_FORM = 0
    PLURAL_FORM = 1

    # Largest number of plural forms any language can have.
    MAX_PLURAL_FORMS = 6

    SPACE_CHAR = '<samp> </samp>'
    NEWLINE_CHAR = '<img alt="" src="/@@/translation-newline" /><br/>\n'
    TAB_CHAR = '<code>[tab]</code>'
    TAB_CHAR_ESCAPED = '<code>' + r'\[tab]' + '</code>'
    NO_BREAK_SPACE_CHAR = '<code>[nbsp]</code>'
    NO_BREAK_SPACE_CHAR_ESCAPED = '<code>' + r'\[nbsp]' + '</code>'
    NARROW_NO_BREAK_SPACE_CHAR = '<code>[nnbsp]</code>'
    NARROW_NO_BREAK_SPACE_CHAR_ESCAPED = '<code>' + r'\[nnbsp]' + '</code>'


class TranslationsBranchImportMode(DBEnumeratedType):
    """How translations from a Bazaar branch should be synchronized."""

    NO_IMPORT = DBItem(1, """
        None

        Do not import any templates or translations from the branch.
        """)

    IMPORT_TEMPLATES = DBItem(2, """
        Import template files

        Import all translation template files found in the branch.
        """)

    IMPORT_TRANSLATIONS = DBItem(3, """
        Import template and translation files

        Import all translation files (templates and translations)
        found in the branch.
        """)

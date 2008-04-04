# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__metaclass__ = type

__all__ = ('TranslationConstants', )

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
    MAX_NUM_PLURAL_FORMS = 4

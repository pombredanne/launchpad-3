# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ('TranslationConstants', )

class TranslationConstants:
    """Set of constants used inside the context of translations."""

    SINGULAR_FORM = 0
    PLURAL_FORM = 1
    SPACE_CHAR = '<samp> </samp>'
    NEWLINE_CHAR = '<img alt="" src="/@@/translation-newline" /><br/>\n'
    TAB_CHAR = '<code>[tab]</code>'
    TAB_CHAR_ESCAPED = '<code>' + r'\[tab]' + '</code>'
    NO_BREAK_SPACE_CHAR = '<code>[nbsp]</code>'
    NO_BREAK_SPACE_CHAR_ESCAPED = '<code>' + r'\[nbsp]' + '</code>'
    MAX_NUM_PLURAL_FORMS = 4

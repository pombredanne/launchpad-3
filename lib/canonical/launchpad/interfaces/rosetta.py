# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ('TranslationConstants', )

def po_message_special(text):
    """Mark up to a piece of text as a piece of special PO message text."""
    return  u'<span class="po-message-special">%s</span>' % text

class TranslationConstants:
    """Set of constants used inside the context of translations."""

    SINGULAR_FORM = 0
    PLURAL_FORM = 1
    SPACE_CHAR = '<span style="padding-right: 10px; background: url(/@@/translation-space) center left no-repeat; white-space: pre;"> </span>'
    # 10px is the width of /@@/translation-space
    NEWLINE_CHAR = '<img alt="" src="/@@/translation-newline" /><br/>\n'
    TAB_CHAR = po_message_special('[tab]')
    TAB_CHAR_ESCAPED = po_message_special(r'\[tab]')

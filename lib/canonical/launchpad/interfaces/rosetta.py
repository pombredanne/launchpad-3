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
    SPACE_CHAR = po_message_special(u'\u2022')
    NEWLINE_CHAR = po_message_special(u'\u21b5') + '<br/>\n'
    TAB_CHAR = po_message_special('[tab]')
    TAB_CHAR_ESCAPED = po_message_special(r'\[tab]')

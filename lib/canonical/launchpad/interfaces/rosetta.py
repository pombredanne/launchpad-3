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
    SPACE_CHAR = '<code style="padding-right: 8px; background: url(/@@/translation-space) center left no-repeat; white-space: pre;"> </code>'
    # 8px should be the width of the /@@/translation-space image.
    NEWLINE_CHAR = '<code><img alt="" src="/@@/translation-newline" /></code><br/>\n'
    TAB_CHAR = po_message_special('[tab]')
    TAB_CHAR_ESCAPED = po_message_special(r'\[tab]')

# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'escape',
    'structured',
    ]

import cgi

from zope.i18n import (
    Message,
    translate,
    )
from zope.interface import implements

from lp.services.webapp.interfaces import IStructuredString
from lp.services.webapp.publisher import get_current_browser_request


def escape(message):
    """Performs translation and sanitizes any HTML present in the message.

    A plain string message will be sanitized ("&", "<" and ">" are
    converted to HTML-safe sequences).  Passing a message that
    provides the `IStructuredString` interface will return a unicode
    string that has been properly escaped.  Passing an instance of a
    Zope internationalized message will cause the message to be
    translated, then santizied.

    :param message: This may be a string, `zope.i18n.Message`,
        `zope.i18n.MessageID`, or an instance of `IStructuredString`.
    """
    if IStructuredString.providedBy(message):
        return message.escapedtext
    else:
        # It is possible that the message is wrapped in an
        # internationalized object, so we need to translate it
        # first. See bug #54987.
        return cgi.escape(
            unicode(
                translate_if_i18n(message)))


def translate_if_i18n(obj_or_msgid):
    """Translate an internationalized object, returning the result.

    Returns any other type of object untouched.
    """
    if isinstance(obj_or_msgid, Message):
        return translate(
            obj_or_msgid,
            context=get_current_browser_request())
    else:
        # Just text (or something unknown).
        return obj_or_msgid


class structured:

    implements(IStructuredString)

    def __init__(self, text, *replacements, **kwreplacements):
        text = translate_if_i18n(text)
        self.text = text
        if replacements and kwreplacements:
            raise TypeError(
                "You must provide either positional arguments or keyword "
                "arguments to structured(), not both.")
        if replacements:
            escaped = []
            for replacement in replacements:
                if isinstance(replacement, structured):
                    escaped.append(unicode(replacement.escapedtext))
                else:
                    escaped.append(cgi.escape(unicode(replacement)))
            self.escapedtext = text % tuple(escaped)
        elif kwreplacements:
            escaped = {}
            for key, value in kwreplacements.iteritems():
                if isinstance(value, structured):
                    escaped[key] = unicode(value.escapedtext)
                else:
                    escaped[key] = cgi.escape(unicode(value))
            self.escapedtext = text % escaped
        else:
            self.escapedtext = unicode(text)

    def __repr__(self):
        return "<structured-string '%s'>" % self.text

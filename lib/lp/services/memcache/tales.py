# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of the memcache: namespace in TALES."""

__metaclass__ = type
__all__ = []


import logging

from zope.tal.talinterpreter import TALInterpreter, I18nMessageTypes


class MemcacheExpr:
    """Namespace to provide memcache caching of page template chunks.

    This namespace is exclusively used in tal:content directives.
    The only sensible way of using this is the following syntax:

    <div tal:content="memcache:1h public">
        [... Potentially expensive page template chunk ...]
    </div>
    """
    def __init__(self, name, expr, engine):
        self._s = expr

    def __call__(self, econtext):
        return MemcacheCallback("key to be calculated from context")

    def __str__(self):
        return 'memcache expression (%s)' % self._s

    def __repr__(self):
        return '<MemcacheExpr %s>' % self._s


class MemcacheCallback:
    """Callback for the customized TALInterpreter to invoke.

    If the memcache hit failed, the TALInterpreter interprets the
    tag contents and invokes this callback, which will store the
    result in memcache against the key calculated by the MemcacheExpr.
    """
    def __init__(self, key):
        self._key = key

    def __call__(self, value):
        logging.info("Caching %s..." % value.strip()[:30])

    def __repr__(self):
        return "<MemcacheCallback %s>" % self._key


# Oh my bleeding eyes! Monkey patching & cargo culting seems the sanest
# way of installing our extensions.

def do_insertText_tal(self, stuff):
    text = self.engine.evaluateText(stuff[0])
    if text is None:
        return
    if text is self.Default:
        self.interpret(stuff[1])
        return
    # Start Launchpad customization
    if isinstance(text, MemcacheCallback):
        callback = text
        self.pushStream(self.StringIO())
        self.interpret(stuff[1])
        text = self.stream.getvalue()
        self.popStream()
        callback(text)
        self.stream_write(text)
        return
    # End Launchpad customization
    if isinstance(text, I18nMessageTypes):
        # Translate this now.
        text = self.translate(text)
    self._writeText(text)
TALInterpreter.bytecode_handlers_tal["insertText"] = do_insertText_tal


# Just like the original, except MemcacheCallback instances are also
# passed through unharmed.
def evaluateText(self, expr):
    text = self.evaluate(expr)
    if (text is None
        or text is self.getDefault()
        or isinstance(text, basestring)
        or isinstance(text, MemcacheCallback)):
        return text
    return unicode(text)
import zope.pagetemplate.engine
zope.pagetemplate.engine.ZopeContextBase.evaluateText = evaluateText


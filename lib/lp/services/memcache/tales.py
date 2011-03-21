# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of the cache: namespace in TALES."""

__metaclass__ = type
__all__ = [
    'MemcacheExpr',
    'MemcacheHit',
    'MemcacheMiss',
    ]


from hashlib import md5
import logging
import os.path

from zope.component import getUtility
from zope.interface import implements
from zope.tal.talinterpreter import (
    I18nMessageTypes,
    TALInterpreter,
    )
from zope.tales.expressions import (
    PathExpr,
    simpleTraverse,
    )
from zope.tales.interfaces import ITALESExpression

from canonical.config import config
from lp.app import versioninfo
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.services.memcache.interfaces import IMemcacheClient
from lp.services.utils import compress_hash

# Request annotation key.
COUNTER_KEY = 'lp.services.memcache.tales.counter'


class MemcacheExpr:
    """Namespace to provide memcache caching of page template chunks.

    This namespace is exclusively used in tal:content directives.
    The only sensible way of using this is the following syntax:

    <div tal:content="cache:public, 1 hour">
        [... Potentially expensive page template chunk ...]
    </div>
    """
    implements(ITALESExpression)

    static_max_age = None # cache expiry if fixed
    dynamic_max_age = None # callable if cache expiry is dynamic.
    dynamic_max_age_unit = None # Multiplier for dynamic cache expiry result.

    def __init__(self, name, expr, engine, traverser=simpleTraverse):
        """expr is in the format "visibility, 42 units".

        visibility is one of...

            public: All users see the same cached information.

            private: Authenticated users see a personal copy of the cached
                     information. Unauthenticated users share a copy of
                     the cached information.

            anonymous: Unauthenticated users use a shared copy of the
                       cached information. Authenticated users don't
                       use the cache. This probably isn't that useful
                       in practice, as Anonymous requests should already
                       be cached by reverse proxies on the production
                       systems.

            authenticated: Authenticated user share a copy of the cached
                           information, and unauthenticated users share
                           a seperate copy. Use this when information is
                           being hidden from unauthenticated users, eg.
                           for bug comments where email addresses are
                           obfuscated for unauthenticated users.

        units is one of 'seconds', 'minutes', 'hours' or 'days'.

        visibility is required. If the cache timeout is not specified,
        it defaults to 'never timeout' (memcache will still purge the
        information when in a LRU fashion when things fill up).
        """
        self._s = expr

        components = [component.strip() for component in expr.split(',')]
        num_components = len(components)
        if num_components == 1:
            self.visibility = components[0]
            max_age = None
            self.extra_key = None
        elif num_components == 2:
            self.visibility, max_age = components
            self.extra_key = None
        elif num_components == 3:
            self.visibility, max_age, extra_key = components
            # Construct a callable that will evaluate the subpath
            # expression when passed a context.
            self.extra_key = PathExpr(name, extra_key, engine, traverser)
        else:
            raise SyntaxError("Too many arguments in cache: expression")

        try:
            self.visibility, modifier = self.visibility.split()
            if modifier == 'param':
                self.include_params = True
            elif modifier == 'noparam':
                self.include_params = False
            else:
                raise SyntaxError(
                    'visibility modifier must be param or noparam')
        except ValueError:
            self.include_params = True

        if self.visibility not in (
            'anonymous', 'public', 'private', 'authenticated'):
            raise SyntaxError(
                'visibility must be anonymous, public, private or '
                'authenticated')

        # Convert the max_age string to an integer number of seconds.
        if max_age is None:
            self.static_max_age = 0 # Never expire.
        else:
            # Extract the unit, if there is one. Unit defaults to seconds.
            try:
                value, unit = max_age.split(' ')
                if unit[-1] == 's':
                    unit = unit[:-1]
                if unit == 'second':
                    unit = 1
                elif unit == 'minute':
                    unit = 60
                elif unit == 'hour':
                    unit = 60 * 60
                elif unit == 'day':
                    unit = 24 * 60 * 60
                else:
                    raise SyntaxError(
                        "Unknown unit %s in cache: expression %s"
                        % (repr(unit), repr(expr)))
            except ValueError:
                value = max_age
                unit = 1

            try:
                self.static_max_age = float(value) * unit
            except (ValueError, TypeError):
                self.dynamic_max_age = PathExpr(
                    name, value, engine, traverser)
                self.dynamic_max_age_unit = unit

    # For use with str.translate to sanitize keys. No control characters
    # allowed, and we skip ':' too since it is a magic separator.
    _key_translate_map = (
        '_'*33 + ''.join(chr(i) for i in range(33, ord(':'))) + '_'
        + ''.join(chr(i) for i in range(ord(':')+1, 127)) + '_' * 129)

    # We strip digits from our LPCONFIG when generating the key
    # to ensure that multiple appserver instances sharing a memcache instance
    # can get hits from each other. For instance edge1 and edge4 are in this
    # situation.
    _lpconfig = config.instance_name.rstrip('0123456789')

    def getKey(self, econtext):
        """We need to calculate a unique key for this cached chunk.

        To ensure content is uniquely identified, we must include:
            - a user id if this chunk is not 'public'
            - the template source file name
            - the position in the source file
            - a counter to cope with cached chunks in loops
            - the revision number of the source tree
            - the config in use
            - the URL and query string
        """
        # We include the URL and query string in the key.
        # We use the full, unadulterated url to calculate a hash.
        # We use a sanitized version in the human readable chunk of
        # the key.
        request = econtext.getValue('request')
        url = str(request.URL)
        if self.include_params:
            url += '?' + str(request.get('QUERY_STRING', ''))
        url = url.encode('utf8') # Ensure it is a byte string.
        sanitized_url = url.translate(self._key_translate_map)

        # We include the source file and position in the source file in
        # the key.
        source_file = os.path.abspath(econtext.source_file)
        source_file = source_file[
            len(os.path.commonprefix([source_file, config.root + '/lib']))+1:]

        # We include the visibility in the key so private information
        # is not leaked. We use 'p' for public information, 'a' for
        # unauthenticated user information, 'l' for information shared
        # between all authenticated users, or ${Person.id} for private
        # information.
        if self.visibility == 'public':
            uid = 'p'
        else:
            logged_in_user = getUtility(ILaunchBag).user
            if logged_in_user is None:
                uid = 'a'
            elif self.visibility == 'authenticated':
                uid = 'l'
            else: # private visibility
                uid = str(logged_in_user.id)

        # The extra_key is used to differentiate items inside loops.
        if self.extra_key is not None:
            # Encode it to to a memcached key safe string. base64
            # isn't suitable for this because it can contain whitespace.
            extra_key = unicode(self.extra_key(econtext)).encode('hex')
        else:
            # If no extra_key was specified, we include a counter in the
            # key that is reset at the start of the request. This
            # ensures we get unique but repeatable keys inside
            # tal:repeat loops.
            extra_key = request.annotations.get(COUNTER_KEY, 0) + 1
            request.annotations[COUNTER_KEY] = extra_key

        # We use pt: as a unique prefix to ensure no clashes with other
        # components using the memcached servers. The order of components
        # below only matters for human readability and memcached reporting
        # tools - it doesn't really matter provided all the components are
        # included and separators used.
        key = "pt:%s:%s,%s:%s:%d,%d:%s,%s" % (
            self._lpconfig, source_file, versioninfo.revno, uid,
            econtext.position[0], econtext.position[1], extra_key,
            sanitized_url,
            )

        # Memcached max key length is 250, so truncate but ensure uniqueness
        # with a hash. A short hash is good, provided it is still unique,
        # to preserve readability as much as possible. We include the
        # unsanitized URL in the hash to ensure uniqueness.
        key_hash = compress_hash(md5(key + url))
        key = key[:250-len(key_hash)] + key_hash

        return key

    def getMaxAge(self, econtext):
        if self.dynamic_max_age is not None:
            return self.dynamic_max_age(econtext) * self.dynamic_max_age_unit
        return self.static_max_age

    def __call__(self, econtext):
        # If we have an 'anonymous' visibility chunk and are logged in,
        # we don't cache. Return the 'default' magic token to interpret
        # the contents.
        if (self.visibility == 'anonymous'
            and getUtility(ILaunchBag).user is not None):
            return econtext.getDefault()

        # Calculate a unique key so we serve the right cached information.
        key = self.getKey(econtext)

        cached_chunk = getUtility(IMemcacheClient).get(key)

        if cached_chunk is None:
            logging.debug("Memcache miss for %s", key)
            return MemcacheMiss(key, self.getMaxAge(econtext), self)
        else:
            logging.debug("Memcache hit for %s", key)
            return MemcacheHit(cached_chunk)

    def __str__(self):
        return 'memcache expression (%s)' % self._s

    def __repr__(self):
        return '<MemcacheExpr %s>' % self._s


class MemcacheMiss:
    """Callback for the customized TALInterpreter to invoke.

    If the memcache hit failed, the TALInterpreter interprets the
    tag contents and invokes this callback, which will store the
    result in memcache against the key calculated by the MemcacheExpr.
    """

    def __init__(self, key, max_age, memcache_expr):
        self._key = key
        self._max_age = max_age
        self._memcache_expr = memcache_expr

    def __call__(self, value):
        if not config.launchpad.is_lpnet:
            # For debugging and testing purposes, prepend a description of
            # the memcache expression used to the stored value.
            rule = '%s [%s seconds]' % (self._memcache_expr, self._max_age)
            value = "<!-- Cache hit: %s -->%s<!-- End cache hit: %s -->" % (
                rule, value, rule)
        getUtility(IMemcacheClient).set(self._key, value, self._max_age)

    def __repr__(self):
        return "<MemcacheCallback %s %d>" % (self._key, self._max_age)


class MemcacheHit:
    """A prerendered chunk retrieved from cache.

    We use a special object so the TALInterpreter knows that this
    information should not be quoted.
    """

    def __init__(self, value):
        self.value = value


# Oh my bleeding eyes! Monkey patching & cargo culting seems the sanest
# way of installing our extensions, which makes me sad.

def do_insertText_tal(self, stuff):
    text = self.engine.evaluateText(stuff[0])
    if text is None:
        return
    if text is self.Default:
        self.interpret(stuff[1])
        return
    # Start Launchpad customization
    if isinstance(text, MemcacheMiss):
        # We got a MemcacheCallback instance. This means we hit a
        # content="cache:..." attribute but there was no valid
        # data in memcache. So we need to interpret the enclosed
        # chunk of template and stuff it in the cache for next time.
        callback = text
        self.pushStream(self.StringIO())
        self.interpret(stuff[1])
        text = self.stream.getvalue()
        self.popStream()
        # Now we have generated the chunk, cache it for next time.
        callback(text)
        # And output it to the currently rendered page, unquoted.
        self.stream_write(text)
        return
    if isinstance(text, MemcacheHit):
        # Got a hit. Include the contents directly into the
        # rendered page, unquoted.
        self.stream_write(text.value)
        return
    # End Launchpad customization
    if isinstance(text, I18nMessageTypes):
        # Translate this now.
        text = self.translate(text)
    self._writeText(text)
TALInterpreter.bytecode_handlers_tal["insertText"] = do_insertText_tal


def evaluateText(self, expr):
    """Replacement for zope.pagetemplate.engine.ZopeContextBase.evaluateText.

    Just like the original, except MemcacheHit and MemcacheMiss
    instances are also passed through unharmed.
    """

    text = self.evaluate(expr)
    if (text is None
        or isinstance(text, (basestring, MemcacheHit, MemcacheMiss))
        or text is self.getDefault()):
        return text
    return unicode(text)
import zope.pagetemplate.engine
zope.pagetemplate.engine.ZopeContextBase.evaluateText = evaluateText

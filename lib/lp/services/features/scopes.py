# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Connect feature flags into scopes where they can be used.

The most common is flags scoped by some attribute of a web request, such as
the page ID or the server name.  But other types of scope can also match code
run from cron scripts and potentially also other places.
"""

__all__ = [
    'HANDLERS',
    'ScopesForScript',
    'ScopesFromRequest',
    'undocumented_scopes',
    ]

__metaclass__ = type

import re

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.services.propertycache import cachedproperty
import canonical.config


undocumented_scopes = set()


class BaseScope():
    """A base class for scope handlers.

    The docstring of subclasses is used on the +feature-info page as
    documentation, so write them accordingly.
    """

    # The regex pattern used to decide if a handler can evaluate a particular
    # scope.  Also used on +feature-info.
    pattern = None

    @cachedproperty
    def compiled_pattern(self):
        """The compiled scope matching regex.  A small optimization."""
        return re.compile(self.pattern)

    def lookup(self, scope_name):
        """Returns true if the given scope name is "active"."""
        raise NotImplementedError('Subclasses of BaseScope must implement '
            'lookup.')


class DefaultScope(BaseScope):
    """The default scope.  Always active."""

    pattern = r'default$'

    def lookup(self, scope_name):
        return True


class BaseWebRequestScope(BaseScope):
    """Base class for scopes that key off web request attributes."""

    def __init__(self, request):
        self.request = request


class PageScope(BaseWebRequestScope):
    """The current page ID.

    Pageid scopes are written as 'pageid:' + the pageid to match.  Pageids
    are treated as a namespace with : and # delimiters.

    For example, the scope 'pageid:Foo' will be active on pages with pageids:
        Foo
        Foo:Bar
        Foo#quux
    """

    pattern = r'pageid:'

    def lookup(self, scope_name):
        """Is the given scope match the current pageid?"""
        pageid_scope = scope_name[len('pageid:'):]
        scope_segments = self._pageid_to_namespace(pageid_scope)
        request_segments = self._request_pageid_namespace
        # In 2.6, this can be replaced with izip_longest
        for pos, name in enumerate(scope_segments):
            if pos == len(request_segments):
                return False
            if request_segments[pos] != name:
                return False
        return True

    @staticmethod
    def _pageid_to_namespace(pageid):
        """Return a list of namespace elements for pageid."""
        # Normalise delimiters.
        pageid = pageid.replace('#', ':')
        # Create a list to walk, empty namespaces are elided.
        return [name for name in pageid.split(':') if name]

    @cachedproperty
    def _request_pageid_namespace(self):
        return tuple(self._pageid_to_namespace(
            self.request._orig_env.get('launchpad.pageid', '')))


class TeamScope(BaseScope):
    """The current user's team memberships.

    Team ID scopes are written as 'team:' + the team name to match.

    The scope 'team:launchpad-beta-users' will match members of the team
    'launchpad-beta-users'.
    """

    pattern = r'team:'

    def lookup(self, scope_name):
        """Is the given scope a team membership?

        This will do a two queries, so we probably want to keep the number of
        team based scopes in use to a small number. (Person.inTeam could be
        fixed to reduce this to one query).
        """
        team_name = scope_name[len('team:'):]
        person = getUtility(ILaunchBag).user
        if person is None:
            return False
        return person.inTeam(team_name)


class ServerScope(BaseScope):
    """Matches the current server.

    For example, the scope server.lpnet is active when is_lpnet is set to True
    in the Launchpad configuration.
    """

    pattern = r'server\.'

    def lookup(self, scope_name):
        """Match the current server as a scope."""
        server_name = scope_name.split('.', 1)[1]
        try:
            return canonical.config.config['launchpad']['is_' + server_name]
        except KeyError:
            pass
        return False


class ScriptScope(BaseScope):
    """Matches the name of the currently running script.

    For example, the scope script:embroider is active in a script called
    "embroider."
    """

    pattern = r'script:'

    def __init__(self, script_name):
        self.script_scope = self.pattern + script_name

    def lookup(self, scope_name):
        """Match the running script as a scope."""
        return scope_name == self.script_scope


# These are the handlers for all of the allowable scopes, listed here so that
# we can for example show all of them in an admin page.  Any new scope will
# need a scope handler and that scope handler has to be added to this list.
# See BaseScope for hints as to what a scope handler should look like.
HANDLERS = set([DefaultScope, PageScope, TeamScope, ServerScope, ScriptScope])


class MultiScopeHandler():
    """A scope handler that combines multiple `BaseScope`s.

    The ordering in which they're added is arbitrary, because precedence is
    determined by the ordering of rules.
    """

    def __init__(self, scopes):
        self.handlers = scopes

    def _findMatchingHandlers(self, scope_name):
        """Find any handlers that match `scope_name`."""
        return [
            handler
            for handler in self.handlers
                if handler.compiled_pattern.match(scope_name)]

    def lookup(self, scope_name):
        """Determine if scope_name applies.

        This method iterates over the configured scope handlers until it
        either finds one that claims the requested scope name matches,
        or the handlers are exhausted, in which case the
        scope name is not a match.
        """
        matching_handlers = self._findMatchingHandlers(scope_name)
        for handler in matching_handlers:
            if handler.lookup(scope_name):
                return True

        # If we didn't find at least one matching handler, then the
        # requested scope is unknown and we want to record the scope for
        # the +flag-info page to display.
        if len(matching_handlers) == 0:
            undocumented_scopes.add(scope_name)


class ScopesFromRequest(MultiScopeHandler):
    """Identify feature scopes based on request state."""

    def __init__(self, request):
        super(ScopesFromRequest, self).__init__([
            DefaultScope(),
            PageScope(request),
            TeamScope(),
            ServerScope()])


class ScopesForScript(MultiScopeHandler):
    """Identify feature scopes for a given script."""

    def __init__(self, script_name):
        super(ScopesForScript, self).__init__([
            DefaultScope(),
            ScriptScope(script_name)])

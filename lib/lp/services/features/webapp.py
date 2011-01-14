# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Connect Feature flags into webapp requests."""

__all__ = []

__metaclass__ = type

from zope.component import getUtility

import canonical.config
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.services.features import per_thread
from lp.services.features.flags import FeatureController
from lp.services.features.rulesource import StormFeatureRuleSource
from lp.services.propertycache import cachedproperty


class DefaultScope():
    """A scope handler for the default scope."""

    def __init__(self, request):
        self.request = request

    def match(self, scope_name):
        """Is the given scope name the default scope?"""
        return scope_name == 'default'

    def lookup(self, scope_name):
        """The default scope is always true."""
        return True


class PageScope():
    """A scope handler that matches on the current page ID."""

    def __init__(self, request):
        self.request = request

    def match(self, scope_name):
        """Is the given scope name a page scope?"""
        return scope_name.startswith('pageid:')

    def lookup(self, scope_name):
        """Is the given scope match the current pageid?

        pageid scopes are written as 'pageid:' + the pageid to match.
        Page ids are treated as a namespace with : and # delimiters.

        E.g. the scope 'pageid:Foo' will affect pages with pageids:
        Foo
        Foo:Bar
        Foo#quux
        """
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


class TeamScope():
    """A scope handler that matches on the current user's team memberships."""

    def __init__(self, request):
        self.request = request

    def match(self, scope_name):
        """Is the given scope name a team scope?"""
        return scope_name.startswith('team:')

    def lookup(self, scope_name):
        """Is the given scope a team membership?

        This will do a two queries, so we probably want to keep the number of
        team based scopes in use to a small number. (Person.inTeam could be
        fixed to reduce this to one query).

        teamid scopes are written as 'team:' + the team name to match.

        E.g. the scope 'team:launchpad-beta-users' will match members of
        the team 'launchpad-beta-users'.
        """
        team_name = scope_name[len('team:'):]
        person = getUtility(ILaunchBag).user
        if person is None:
            return False
        return person.inTeam(team_name)


class ServerScope():
    """A scope handler that matches on the server (e.g., server.lpnet)."""

    def __init__(self, request):
        self.request = request


    def match(self, scope_name):
        """Is the given scope name a server scope?"""
        return scope_name.startswith('server.')

    def lookup(self, scope_name):
        """Match the current server as a scope."""
        server_name = scope_name.split('.', 1)[1]
        try:
            return canonical.config.config['launchpad']['is_' + server_name]
        except KeyError:
            pass
        return False


# These are the handlers for all of the allowable scopes.  Any new scope will
# need a scope handler and that scope handler has to be added to this list.
HANDLERS = [DefaultScope, PageScope, TeamScope, ServerScope]


class ScopesFromRequest():
    """Identify feature scopes based on request state."""

    def __init__(self, request):
        self.request = request
        self.handlers = [f(request) for f in HANDLERS]

    def lookup(self, scope_name):
        """Determine if scope_name applies to this request.

        This method iterates over the configured scope hanlders until it
        either finds one that claims the requested scope name is a match for
        the current request or the handlers are exhuasted, in which case the
        scope name is not a match.
        """
        found_a_handler = False
        for handler in self.handlers:
            if handler.match(scope_name):
                found_a_handler = True
                if handler.lookup(scope_name):
                    return True

        # If we didn't find at least one matching handler, then the requested
        # scope is unknown and we want to alert the caller that they did
        # something wrong.
        if not found_a_handler:
            raise LookupError('Unknown scope: %r.  This can result from a '
            'typo or perhaps you need to create a new scope handler.'
            % (scope_name,))


def start_request(event):
    """Register FeatureController."""
    event.request.features = per_thread.features = FeatureController(
        ScopesFromRequest(event.request).lookup,
        StormFeatureRuleSource())


def end_request(event):
    """Done with this FeatureController."""
    event.request.features = per_thread.features = None

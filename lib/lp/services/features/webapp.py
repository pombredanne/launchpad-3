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

#        Currently supports the following scopes:
#         - default
#         - server.lpnet etc (thunks through to the config is_lpnet)
#         - pageid:
#           This scope works on a namespace model: for a page
#           with pageid SomeType:+view#subselector
#           The following page ids scopes will match:
#             - pageid:   (but use 'default' as it is simpler)
#             - pageid:SomeType
#             - pageid:SomeType:+view
#             - pageid:SomeType:+view#subselector
#         - team:
#           This scope looks up a team. For instance
#             - team:launchpad-beta-users


class DefaultScope():
    """A scope handler for the default scope."""

    def __init__(self, request):
        self.request = request

    def lookup(self, scope_name):
        """The default scope.  Matches only the string "default"."""
        return scope_name == 'default' or None


class PageScope():
    """A scope handler that matches on the current page ID."""

    def __init__(self, request):
        self.request = request

    def lookup(self, scope_name):
        """Is the given scope a matching pageid?

        pageid scopes are written as 'pageid:' + the pageid to match.
        Page ids are treated as a namespace with : and # delimiters.

        E.g. the scope 'pageid:Foo' will affect pages with pageids:
        Foo
        Foo:Bar
        Foo#quux
        """
        if not scope_name.startswith('pageid:'):
            return None
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

    def lookup(self, scope_name):
        """Is the given scope a team membership?

        This will do a two queries, so we probably want to keep the number of
        team based scopes in use to a small number. (Person.inTeam could be
        fixed to reduce this to one query).

        teamid scopes are written as 'team:' + the team name to match.

        E.g. the scope 'team:launchpad-beta-users' will match members of
        the team 'launchpad-beta-users'.
        """
        if not scope_name.startswith('team:'):
            return None
        team_name = scope_name[len('team:'):]
        person = getUtility(ILaunchBag).user
        if person is None:
            return False
        return person.inTeam(team_name)


class ServerScope():
    """A scope handler that matches on the server (e.g., server.lpnet)."""

    def __init__(self, request):
        self.request = request

    def lookup(self, scope_name):
        """Match the current server as a scope."""
        if not scope_name.startswith('server.'):
            return None
        server_name = scope_name.split('.', 1)[1]
        try:
            return canonical.config.config['launchpad']['is_' + server_name]
        except KeyError:
            pass
        return False


class ScopesFromRequest():
    """Identify feature scopes based on request state."""

    handler_factories = [DefaultScope, PageScope, TeamScope, ServerScope]

    def __init__(self, request):
        self.request = request
        self.handlers = [f(request) for f in self.handler_factories]

    def lookup(self, scope_name):
        """Determine if scope_name applies to this request.

        This method iterates over the configured scope hanlders until it
        either finds one that claims the requested scope name is a match for
        the current request or the handlers are exhuasted, in which case the
        scope name is not a match.
        """
        results = [handler.lookup(scope_name) for handler in self.handlers]
        if True in results:
            return True
        if False in results:
            return False
        raise LookupError('Unknown scope: %r' % (scope_name,))


def start_request(event):
    """Register FeatureController."""
    event.request.features = per_thread.features = FeatureController(
        ScopesFromRequest(event.request).lookup,
        StormFeatureRuleSource())


def end_request(event):
    """Done with this FeatureController."""
    event.request.features = per_thread.features = None

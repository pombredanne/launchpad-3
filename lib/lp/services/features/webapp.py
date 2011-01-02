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


class ScopesFromRequest(object):
    """Identify feature scopes based on request state."""

    def __init__(self, request):
        self._request = request

    def lookup(self, scope_name):
        """Determine if scope_name applies to this request.

        Currently supports the following scopes:
         - default
         - server.lpnet etc (thunks through to the config is_lpnet)
         - pageid:
           This scope works on a namespace model: for a page
           with pageid SomeType:+view#subselector
           The following page ids scopes will match:
             - pageid:   (but use 'default' as it is simpler)
             - pageid:SomeType
             - pageid:SomeType:+view
             - pageid:SomeType:+view#subselector
         - team:
           This scope looks up a team. For instance
             - team:launchpad-beta-users
        """
        if scope_name == 'default':
            return True
        if scope_name.startswith('pageid:'):
            return self._lookup_pageid(scope_name[len('pageid:'):])
        if scope_name.startswith('team:'):
            return self._lookup_team(scope_name[len('team:'):])
        parts = scope_name.split('.')
        if len(parts) == 2:
            if parts[0] == 'server':
                try:
                    return canonical.config.config['launchpad'][
                        'is_' + parts[1]]
                except KeyError:
                    return False

    def _lookup_pageid(self, pageid_scope):
        """Lookup a pageid as a scope.

        pageid scopes are written as 'pageid:' + the pageid to match.
        Page ids are treated as a namespace with : and # delimiters.

        E.g. the scope 'pageid:Foo' will affect pages with pageids:
        Foo
        Foo:Bar
        Foo#quux
        """
        scope_segments = self._pageid_to_namespace(pageid_scope)
        request_segments = self._request_pageid_namespace
        # In 2.6, this can be replaced with izip_longest
        for pos, name in enumerate(scope_segments):
            if pos == len(request_segments):
                return False
            if request_segments[pos] != name:
                return False
        return True

    def _lookup_team(self, team_name):
        """Lookup a team membership as a scope.

        This will do a two queries, so we probably want to keep the number of
        team based scopes in use to a small number. (Person.inTeam could be
        fixed to reduce this to one query).

        teamid scopes are written as 'team:' + the team name to match.

        E.g. the scope 'team:launchpad-beta-users' will match members of
        the team 'launchpad-beta-users'.
        """
        person = getUtility(ILaunchBag).user
        if person is None:
            return False
        return person.inTeam(team_name)

    def _pageid_to_namespace(self, pageid):
        """Return a list of namespace elements for pageid."""
        # Normalise delimiters.
        pageid = pageid.replace('#', ':')
        # Create a list to walk, empty namespaces are elided.
        return [name for name in pageid.split(':') if name]

    @cachedproperty
    def _request_pageid_namespace(self):
        return tuple(self._pageid_to_namespace(
            self._request._orig_env.get('launchpad.pageid', '')))


def start_request(event):
    """Register FeatureController."""
    event.request.features = per_thread.features = FeatureController(
        ScopesFromRequest(event.request).lookup,
        StormFeatureRuleSource())


def end_request(event):
    """Done with this FeatureController."""
    event.request.features = per_thread.features = None

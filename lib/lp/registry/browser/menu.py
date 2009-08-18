# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Shared menus."""

__metaclass__ = type
__all__ = [
    'IRegistryCollectionNavigationMenu',
    'RegistryCollectionNavigationMenu',
    'TopLevelMenuMixin',
    ]


from zope.component import getUtility
from zope.interface import Interface

from canonical.launchpad.webapp.menu import Link, NavigationMenu
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities


class TopLevelMenuMixin:
    """Menu shared by top level collection objects."""

    def projects(self):
        return Link('/projects/', 'View projects', icon='info')

    def distributions(self):
        return Link('/distros/', 'View distributions', icon='info')

    def people(self):
        return Link('/people/', 'View people', icon='info')

    def meetings(self):
        return Link('/sprints/', 'View meetings', icon='info')

    def project_groups(self):
        return Link('/projectgroups', 'View project groups', icon='info')

    def register_project(self):
        text = 'Register a project'
        enabled = self.user is not None
        return Link('/projects/+new', text, icon='add', enabled=enabled)

    def register_team(self):
        text = 'Register a team'
        enabled = self.user is not None
        return Link('/people/+newteam', text, icon='add', enabled=enabled)

    def create_account(self):
        text = 'Create an account'
        # Only enable this link for anonymous users.
        enabled = self.context.user is None
        return Link('/people/+login', text, icon='add', enabled=enabled)

    def request_merge(self):
        text = 'Request a merge'
        enabled = self.user is not None
        return Link('/people/+requestmerge', text, icon='edit',
                    enabled=enabled)

    def admin_merge_people(self):
        text = 'Merge people'
        enabled = (self.user is not None and
                   self.user.inTeam(getUtility(ILaunchpadCelebrities).admin))
        return Link('/people/+adminpeoplemerge', text, icon='edit',
                    enabled=enabled)

    def admin_merge_teams(self):
        text = 'Merge teams'
        enabled = (self.user is not None and
                   self.user.inTeam(getUtility(ILaunchpadCelebrities).admin))
        return Link('/people/+adminteammerge', text, icon='edit',
                    enabled=enabled)


class IRegistryCollectionNavigationMenu(Interface):
    """Marker interface for top level registry collection navigation menu."""


class RegistryCollectionNavigationMenu(NavigationMenu, TopLevelMenuMixin):
    """Navigation menu for people search."""

    usedfor = IRegistryCollectionNavigationMenu
    facet = 'overview'

    links = [
        'projects',
        'project_groups',
        'distributions',
        'people',
        'meetings',
        'register_team',
        'register_project',
        'create_account',
        'request_merge',
        'admin_merge_people',
        'admin_merge_teams'
        ]

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Shared menus."""

__metaclass__ = type
__all__ = [
    'IRegistryCollectionNavigationMenu',
    'RegistryCollectionActionMenuBase',
    'RegistryCollectionNavigationMenu',
    'TopLevelMenuMixin',
    ]


from zope.interface import Interface

from canonical.launchpad.webapp.menu import (
    Link, NavigationMenu, enabled_with_permission)


class TopLevelMenuMixin:
    """Menu shared by top level collection objects."""

    def projects(self):
        return Link('/projects/', 'Projects')

    def distributions(self):
        return Link('/distros/', 'Distributions')

    def people(self):
        return Link('/people/', 'People')

    def meetings(self):
        return Link('/sprints/', 'Meetings')

    def project_groups(self):
        return Link('/projectgroups', 'Project groups')

    def register_project(self):
        text = 'Register a project'
        return Link('/projects/+new', text, icon='add')

    def register_team(self):
        text = 'Register a team'
        return Link('/people/+newteam', text, icon='add')

    def create_account(self):
        text = 'Create an account'
        # Only enable this link for anonymous users.
        enabled = self.user is None
        return Link('/people/+login', text, icon='add', enabled=enabled)

    @enabled_with_permission('launchpad.View')
    def request_merge(self):
        text = 'Request a merge'
        return Link('/people/+requestmerge', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def admin_merge_people(self):
        text = 'Merge people'
        return Link('/people/+adminpeoplemerge', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def admin_merge_teams(self):
        text = 'Merge teams'
        return Link('/people/+adminteammerge', text, icon='edit')


class IRegistryCollectionNavigationMenu(Interface):
    """Marker interface for top level registry collection navigation menu."""


class RegistryCollectionNavigationMenu(NavigationMenu, TopLevelMenuMixin):
    """Navigation menu for top level registry collections."""

    usedfor = IRegistryCollectionNavigationMenu
    facet = 'overview'

    links = [
        'projects',
        'project_groups',
        'distributions',
        'people',
        'meetings',
        ]


class RegistryCollectionActionMenuBase(NavigationMenu, TopLevelMenuMixin):
    """Action menu for top level registry collections.

    Because of the way menus work, you need to subclass this menu class and
    set the `usedfor` attribute on the subclass.  `usedfor` should point to
    the interface of the context object, so we can't do that for you.

    You should also set the `links` attribute to get just the menu items you
    want for the collection's overview page.
    """
    facet = 'overview'

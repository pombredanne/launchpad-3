# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Shared menus."""

__metaclass__ = type
__all__ = [
    'TopLevelMenuMixin',
    ]


from canonical.launchpad.webapp.menu import Link


class TopLevelMenuMixin:
    """Menu shared by top level collection objects."""

    def products(self):
        return Link('/projects/', 'View projects', icon='info')

    def distributions(self):
        return Link('/distros/', 'View distributions', icon='info')

    def people(self):
        return Link('/people/', 'View people', icon='info')

    def meetings(self):
        return Link('/sprints/', 'View meetings', icon='info')

    def register_project(self):
        text = 'Register a project'
        return Link('/projects/+new', text, icon='add')

    def register_team(self):
        text = 'Register a team'
        return Link('/people/+newteam', text, icon='add')

    def create_account(self):
        text = 'Create an account'
        return Link('/people/+login', text, icon='add')

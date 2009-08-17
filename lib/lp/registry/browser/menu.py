# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Shared menus."""

__metaclass__ = type
__all__ = [
    'TopLevelContextMenuMixin',
    ]


from canonical.launchpad.webapp import Link


class TopLevelContextMenuMixin:
    """Context menu shared by top level collection objects."""

    def products(self):
        return Link('/projects/', 'View projects')

    def distributions(self):
        return Link('/distros/', 'View distributions')

    def people(self):
        return Link('/people/', 'View people')

    def meetings(self):
        return Link('/sprints/', 'View meetings')

    def register_project(self):
        text = 'Register a project'
        return Link('/projects/+new', text, icon='add')

    def register_team(self):
        text = 'Register a team'
        return Link('/people/+newteam', text, icon='add')

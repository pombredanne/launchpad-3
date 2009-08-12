# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Project-related View Classes"""

__metaclass__ = type

__all__ = [
    'ProjectTranslationsMenu',
    'ProjectView',
    ]

from canonical.launchpad.webapp import (
    ApplicationMenu, enabled_with_permission, Link, LaunchpadView)
from canonical.launchpad.webapp.menu import NavigationMenu
from lp.registry.interfaces.project import IProject


class ProjectTranslationsMenu(NavigationMenu):

    usedfor = IProject
    facet = 'translations'
    links = ['products', 'changetranslators']

    @enabled_with_permission('launchpad.Edit')
    def changetranslators(self):
        text = 'Settings'
        return Link('+changetranslators', text, icon='edit')

    def products(self):
        text = 'Products'
        return Link('', text)


class ProjectView(LaunchpadView):
    pass

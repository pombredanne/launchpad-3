# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Project-related View Classes"""

__metaclass__ = type

__all__ = [
    'ProjectChangeTranslatorsView',
    'ProjectTranslationsMenu',
    'ProjectView',
    ]

from canonical.launchpad.webapp import (
    action, canonical_url, enabled_with_permission, Link, LaunchpadView)
from canonical.launchpad.webapp.menu import NavigationMenu
from lp.registry.interfaces.project import IProject
from lp.registry.browser.project import ProjectEditView
from lp.translations.browser.translations import TranslationsMixin


class ProjectTranslationsMenu(NavigationMenu):

    usedfor = IProject
    facet = 'translations'
    links = ['products', 'settings', 'overview']

    @enabled_with_permission('launchpad.Edit')
    def settings(self):
        text = 'Settings'
        return Link('+changetranslators', text, icon='edit')

    def products(self):
        text = 'Products'
        return Link('', text)

    def overview(self):
        text = 'Overview'
        link = canonical_url(self.context, rootsite='translations')
        return Link(link, text, icon='translation')


class ProjectView(LaunchpadView):
    """A view for `IProject` in the translations context."""

    label = "Translatable applications"

    @property
    def untranslatables(self):
        translatables = set(self.context.translatables())
        all_products = set(self.context.products)
        return list(all_products - translatables)


class ProjectChangeTranslatorsView(TranslationsMixin, ProjectEditView):
    label = "Set permissions and policies"
    page_title = "Permissions and policies"
    field_names = ["translationgroup", "translationpermission"]

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def next_url(self):
        return self.cancel_url

    @action('Change', name='change')
    def edit(self, action, data):
        self.updateContextFromData(data)

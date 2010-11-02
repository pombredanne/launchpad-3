# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ProjectGroup-related View Classes"""

__metaclass__ = type

__all__ = [
    'ProjectSettingsView',
    'ProjectTranslationsMenu',
    'ProjectView',
    ]

from canonical.launchpad.webapp import (
    action,
    canonical_url,
    enabled_with_permission,
    LaunchpadView,
    Link,
    )
from canonical.launchpad.webapp.menu import NavigationMenu
from lp.registry.browser.project import ProjectEditView
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.services.propertycache import cachedproperty
from lp.translations.browser.translations import TranslationsMixin


class ProjectTranslationsMenu(NavigationMenu):

    usedfor = IProjectGroup
    facet = 'translations'
    links = ['products', 'settings', 'overview']

    @enabled_with_permission('launchpad.TranslationsAdmin')
    def settings(self):
        text = 'Change permissions'
        return Link('+settings', text, icon='edit', site='translations')

    def products(self):
        text = 'Products'
        return Link('', text, site='translations')

    def overview(self):
        text = 'Overview'
        link = canonical_url(self.context, rootsite='translations')
        return Link(link, text, icon='translation')


class ProjectView(LaunchpadView):
    """A view for `IProjectGroup` in the translations context."""

    label = "Translatable applications"

    @property
    def untranslatables(self):
        translatables = set(self.context.translatables())
        all_products = set(self.context.products)
        return list(all_products - translatables)


class ProjectSettingsView(TranslationsMixin, ProjectEditView):
    label = "Set permissions and policies"
    page_title = "Permissions and policies"
    field_names = ["translationgroup", "translationpermission"]

    @property
    def cancel_url(self):
        return canonical_url(self.context, rootsite="translations")

    next_url = cancel_url

    @action('Change', name='change')
    def edit(self, action, data):
        self.updateContextFromData(data)

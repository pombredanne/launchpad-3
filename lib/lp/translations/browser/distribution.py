# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translations browser views for distributions."""

__metaclass__ = type

__all__ = [
    'DistributionLanguagePackAdminView',
    'DistributionView',
    ]

import operator

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import (
    action, canonical_url, enabled_with_permission, LaunchpadEditFormView,
    LaunchpadView, Link)
from canonical.launchpad.webapp.menu import NavigationMenu
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import DistroSeriesStatus


class DistributionTranslationsMenu(NavigationMenu):

    usedfor = IDistribution
    facet = 'translations'
    links = ['overview', 'settings', 'language_pack_admin', 'imports']

    def overview(self):
        text = 'Overview'
        link = canonical_url(self.context, rootsite='translations')
        return Link(link, text)

    @enabled_with_permission('launchpad.Edit')
    def settings(self):
        text = 'Settings'
        return Link('+settings', text)

    @enabled_with_permission('launchpad.TranslationsAdmin')
    def language_pack_admin(self):
        text = 'Language pack admin'
        return Link('+select-language-pack-admin', text, icon='edit')

    def imports(self):
        text = 'Import queue'
        return Link('+imports', text)


class DistributionLanguagePackAdminView(LaunchpadEditFormView):
    """Browser view to change the language pack administrator."""

    schema = IDistribution
    label = "Change the language pack administrator"
    field_names = ['language_pack_admin']

    @action("Change", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)


class DistributionView(LaunchpadView):
    """Default Distribution view class."""

    @cachedproperty
    def translation_focus(self):
        """Return the IDistroSeries where the translators should work.

        If ther isn't a defined focus, we return latest series.
        """
        if self.context.translation_focus is None:
            return self.context.currentseries
        else:
            return self.context.translation_focus

    def secondary_translatable_serieses(self):
        """Return a list of IDistroSeries that aren't the translation_focus.

        It only includes the ones that are still supported.
        """
        serieses = [
            series
            for series in self.context.serieses
            if (series.status != DistroSeriesStatus.OBSOLETE
                and (self.translation_focus is None or
                     self.translation_focus.id != series.id))
            ]

        return sorted(serieses, key=operator.attrgetter('version'),
                      reverse=True)


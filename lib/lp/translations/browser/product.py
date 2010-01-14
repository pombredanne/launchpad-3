# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translations browser views for products."""

__metaclass__ = type

__all__ = [
    'ProductChangeTranslatorsView',
    'ProductTranslationsMenu',
    'ProductView',
    ]

from zope.security.proxy import removeSecurityProxy

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import (
    LaunchpadView, Link, canonical_url, enabled_with_permission)
from canonical.launchpad.webapp.menu import NavigationMenu
from lp.registry.interfaces.product import IProduct
from lp.registry.model.productseries import ProductSeries
from lp.registry.browser.product import ProductEditView
from lp.translations.browser.translations import TranslationsMixin


class ProductTranslationsMenu(NavigationMenu):

    usedfor = IProduct
    facet = 'translations'
    links = (
        'overview',
        'settings',
        'translationdownload',
        'imports',
        )

    def imports(self):
        text = 'Import queue'
        return Link('+imports', text)

    @enabled_with_permission('launchpad.Edit')
    def settings(self):
        text = 'Settings'
        return Link('+changetranslators', text, icon='edit')

    @enabled_with_permission('launchpad.AnyPerson')
    def translationdownload(self):
        text = 'Download'
        preferred_series = self.context.primary_translatable
        enabled = (self.context.official_rosetta and
            preferred_series is not None)
        link = ''
        if enabled:
            link = '%s/+export' % preferred_series.name
            text = 'Download "%s"' % preferred_series.name

        return Link(link, text, icon='download', enabled=enabled)

    def overview(self):
        text = 'Overview'
        link = canonical_url(self.context, rootsite='translations')
        return Link(link, text, icon='translation')


class ProductChangeTranslatorsView(TranslationsMixin, ProductEditView):
    label = "Set permissions and policies"
    page_title = "Permissions and policies"
    field_names = ["translationgroup", "translationpermission"]

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def next_url(self):
        return self.cancel_url


class ProductView(LaunchpadView):

    __used_for__ = IProduct

    label = "Translation overview"

    @cachedproperty
    def has_translations(self):
        """Whether this product has translatable templates."""
        return (self.context.official_rosetta and self.primary_translatable)

    @cachedproperty
    def primary_translatable(self):
        """Return the context's primary translatable if it's a product series.
        """
        translatable = self.context.primary_translatable

        if not isinstance(removeSecurityProxy(translatable), ProductSeries):
            return None

        return translatable

    @cachedproperty
    def untranslatable_series(self):
        """Return series which are not yet set up for translations."""
        all_series = set(self.context.series)
        translatable = set(self.context.translatable_series)
        return all_series - translatable

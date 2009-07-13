# Copyright 2009 Canonical Ltd.  All rights reserved.

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
    LaunchpadEditFormView, LaunchpadView, Link, canonical_url,
    enabled_with_permission)
from canonical.launchpad.webapp.menu import NavigationMenu
from lp.registry.interfaces.product import IProduct
from lp.registry.model.productseries import ProductSeries
from lp.translations.browser.translations import TranslationsMixin

class ProductTranslationsMenu(NavigationMenu):

    usedfor = IProduct
    facet = 'translations'
    links = (
        'overview',
        'translators',
        'translationdownload',
        'imports',
        )

    def imports(self):
        text = 'Import queue'
        return Link('+imports', text)

    @enabled_with_permission('launchpad.Edit')
    def translators(self):
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


class ProductChangeTranslatorsView(TranslationsMixin, LaunchpadEditFormView):
    label = "Select a new translation group"
    field_names = ["translationgroup", "translationpermission"]


class ProductView(LaunchpadView):

    __used_for__ = IProduct

    @cachedproperty
    def uses_translations(self):
        """Whether this product has translatable templates."""
        return (self.context.official_rosetta and self.primary_translatable)

    @cachedproperty
    def primary_translatable(self):
        """Return a dictionary with the info for a primary translatable.

        If there is no primary translatable object, returns an empty
        dictionary.

        The dictionary has the keys:
         * 'title': The title of the translatable object.
         * 'potemplates': a set of PO Templates for this object.
         * 'base_url': The base URL to reach the base URL for this object.
        """
        translatable = self.context.primary_translatable
        naked_translatable = removeSecurityProxy(translatable)

        if (translatable is None or
            not isinstance(naked_translatable, ProductSeries)):
            return {}

        return {
            'title': translatable.title,
            'potemplates': translatable.getCurrentTranslationTemplates(),
            'base_url': canonical_url(translatable)
            }

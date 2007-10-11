# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'HelpTranslateButtonView',
    'RosettaApplicationView',
    'RosettaStatsView',
    'RosettaApplicationNavigation',
    'TranslationGroupAndPermissionInfoView',
    'TranslateRedirectView',
    'TranslationsMixin',
    'TranslationsRedirectView',
    ]

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IRequestPreferredLanguages, ICountry, ILaunchpadCelebrities,
    IRosettaApplication, ILanguageSet, ILaunchpadRoot,
    IProductSet)
from canonical.launchpad.layers import TranslationsLayer
from canonical.launchpad.webapp import Navigation, stepto, canonical_url
from canonical.launchpad.webapp.batching import BatchNavigator


class HelpTranslateButtonView:
    """View that renders a button to help translate its context."""

    def __call__(self):
        return """
              <a href="%s">
                <img
                  alt="Help translate"
                  src="/+icing/but-sml-helptranslate.gif"
                />
              </a>
        """ % canonical_url(self.context, rootsite='translations')


class TranslationGroupAndPermissionInfoView:
    """View that renders the translation group information."""

    def __call__(self):
        if self.context.translationgroup is None:
            translation_group_content = 'Not assigned'
        else:
            translation_group_content = '<a href="%s">%s</a>' % (
                canonical_url(self.context.translationgroup,
                              rootsite='translations'),
                self.context.translationgroup.title)

        return '''
            <tr>
              <th>Translation group:</th>
              <td>%s</td>
            </tr>
            <tr>
              <th>Translations:</th>
              <td>%s</td>
            </tr>''' % (
                translation_group_content,
                self.context.translationpermission.title)


class TranslationsMixin:
    """Translation mixin that provides language handling."""

    @property
    def translatable_languages(self):
        """Return a set of the Person's translatable languages."""
        english = getUtility(ILanguageSet)['en']
        languages = helpers.preferred_or_request_languages(self.request)
        if english in languages:
            return [lang for lang in languages if lang != english]
        return languages


class RosettaApplicationView(TranslationsMixin):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def ubuntu_translationseries(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        series = ubuntu.translation_focus
        if series is None:
            return ubuntu.currentseries
        else:
            return series

    def ubuntu_languages(self):
        langs = []
        series = self.ubuntu_translationseries
        for language in self.languages:
            langs.append(series.getDistroSeriesLanguageOrDummy(language))
        return langs

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return IRequestPreferredLanguages(
            self.request).getPreferredLanguages()

    @cachedproperty
    def batchnav(self):
        """Return a BatchNavigator for the list of translatable products."""
        products = getUtility(IProductSet)
        return BatchNavigator(products.getTranslatables(),
                              self.request)

    def rosettaAdminEmail(self):
        return config.rosetta.rosettaadmin.email


class RosettaStatsView:
    """A view class for objects that support IRosettaStats. This is mainly
    used for the sortable untranslated percentage."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sortable_untranslated(self):
        return '%06.2f' % self.context.untranslatedPercentage()


class RosettaApplicationNavigation(Navigation):

    usedfor = IRosettaApplication

    newlayer = TranslationsLayer

    @stepto('groups')
    def redirect_groups(self):
        """Redirect /translations/+groups to Translations root site."""
        target_url = canonical_url(
            getUtility(ILaunchpadRoot), rootsite='translations')
        return self.redirectSubTree(
            target_url + '+groups', status=301)

    @stepto('imports')
    def redirect_imports(self):
        """Redirect /translations/imports to Translations root site."""
        target_url = canonical_url(
            getUtility(ILaunchpadRoot), rootsite='translations')
        return self.redirectSubTree(
            target_url + '+imports', status=301)

    @stepto('projects')
    def projects(self):
        # DEPRECATED
        return getUtility(IProductSet)

    @stepto('products')
    def products(self):
        # DEPRECATED
        return getUtility(IProductSet)


class PageRedirectView:
    """Redirects to translations site for the given page."""

    def __init__(self, context, request, page):
        self.context = context
        self.request = request
        self.page = page

    def __call__(self):
        """Redirect to self.page in the translations site."""
        self.request.response.redirect(
            '/'.join([
                canonical_url(self.context, rootsite='translations'),
                self.page
                ]), status=301)


class TranslateRedirectView(PageRedirectView):
    """Redirects to translations site for +translate page."""

    def __init__(self, context, request):
        PageRedirectView.__init__(self, context, request, '+translate')


class TranslationsRedirectView(PageRedirectView):
    """Redirects to translations site for +translations page."""

    def __init__(self, context, request):
        PageRedirectView.__init__(self, context, request, '+translations')

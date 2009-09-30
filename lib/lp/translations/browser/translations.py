# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'HelpTranslateButtonView',
    'RosettaApplicationView',
    'RosettaStatsView',
    'RosettaApplicationNavigation',
    'TranslateRedirectView',
    'TranslationsLanguageBreadcrumb',
    'TranslationsMixin',
    'TranslationsRedirectView',
    'TranslationsVHostBreadcrumb',
    ]

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad import helpers
from canonical.launchpad.interfaces.geoip import IRequestPreferredLanguages
from canonical.launchpad.interfaces.launchpad import (
    ILaunchpadCelebrities, IRosettaApplication)
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from lp.registry.interfaces.product import IProductSet
from lp.services.worlddata.interfaces.country import ICountry
from lp.registry.interfaces.person import IPersonSet
from canonical.launchpad.layers import TranslationsLayer
from canonical.launchpad.webapp import (
    LaunchpadView, Navigation, stepto, canonical_url)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.breadcrumb import Breadcrumb


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


class TranslationsMixin:
    """Provide Translations specific properties."""

    @property
    def translatable_languages(self):
        """Return a set of the Person's translatable languages."""
        english = getUtility(ILaunchpadCelebrities).english
        languages = helpers.preferred_or_request_languages(self.request)
        if english in languages:
            return [lang for lang in languages if lang != english]
        return languages

    @cachedproperty
    def answers_url(self):
        return canonical_url(
            getUtility(ILaunchpadCelebrities).lp_translations,
            rootsite='answers')


class RosettaApplicationView(TranslationsMixin):
    """View for various top-level Translations pages."""

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
        return config.rosettaadmin.email

    @property
    def launchpad_users_team(self):
        """The url of the launchpad-users team."""
        team = getUtility(IPersonSet).getByName('launchpad-users')
        return canonical_url(team)


class TranslatableProductsView(LaunchpadView):
    """List of translatable products."""
    label = "Projects with translations in Launchpad"

    @cachedproperty
    def batchnav(self):
        """Navigate the list of translatable products."""
        return BatchNavigator(
            getUtility(IProductSet).getTranslatables(), self.request)


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


class TranslationsVHostBreadcrumb(Breadcrumb):
    rootsite = 'translations'
    text = 'Translations'


class TranslationsLanguageBreadcrumb(Breadcrumb):
    """Breadcrumb for objects with language."""
    @property
    def text(self):
        return self.context.language.displayname

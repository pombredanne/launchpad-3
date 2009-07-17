# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Translations view classes related to `IDistroSeries`."""

__metaclass__ = type

__all__ = [
    'DistroSeriesLanguagePackView',
    'DistroSeriesTemplatesView',
    'DistroSeriesTranslationsAdminView',
    'DistroSeriesTranslationsMenu',
    'DistroSeriesView',
    ]

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import helpers
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp import action
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.launchpadform import LaunchpadEditFormView
from canonical.launchpad.webapp.menu import (
    Link, NavigationMenu, enabled_with_permission)
from canonical.launchpad.webapp.publisher import (
    canonical_url, LaunchpadView)

from lp.registry.interfaces.distroseries import IDistroSeries
from lp.translations.browser.translations import TranslationsMixin
from lp.translations.interfaces.distroserieslanguage import (
    IDistroSeriesLanguageSet)
from lp.translations.interfaces.potemplate import IPOTemplateSet


class DistroSeriesTranslationsAdminView(LaunchpadEditFormView):
    schema = IDistroSeries

    field_names = ['hide_all_translations', 'defer_translation_imports']

    def initialize(self):
        LaunchpadEditFormView.initialize(self)
        self.label = 'Change translation options of %s' % self.context.title

    @action("Change")
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.request.response.addInfoNotification(
            'Your changes have been applied.')

        self.next_url = canonical_url(self.context)


class DistroSeriesLanguagePackView(LaunchpadEditFormView):
    """Browser view to manage used language packs."""
    schema = IDistroSeries
    label = ""

    def is_langpack_admin(self, action=None):
        """Find out if the current user is a Language Packs Admin.

        This group of users have launchpad.LanguagePacksAdmin rights on
        the DistroSeries but are not general Rosetta admins.

        :returns: True if the user is a Language Pack Admin (but not a 
            Rosetta admin)."""
        return (check_permission("launchpad.LanguagePacksAdmin",
                                 self.context) and not
                check_permission("launchpad.TranslationsAdmin", self.context))

    def is_translations_admin(self, action=None):
        """Find out if the current user is a Rosetta Admin.

        :returns: True if the user is a Rosetta Admin.
        """
        return check_permission("launchpad.TranslationsAdmin", self.context)

    @property
    def is_admin(self):
        return self.is_langpack_admin() or self.is_translations_admin()

    def initialize(self):
        self.old_request_value = (
            self.context.language_pack_full_export_requested)
        if self.is_translations_admin():
            self.field_names = [
                'language_pack_base',
                'language_pack_delta',
                'language_pack_proposed',
                'language_pack_full_export_requested',
            ]
        elif self.is_langpack_admin():
            self.field_names = ['language_pack_full_export_requested']
        else:
            self.field_names = []
        super(DistroSeriesLanguagePackView, self).initialize()
        self.displayname = '%s %s' % (
            self.context.distribution.displayname,
            self.context.version)
        self.page_title = "Language packs for %s" % self.displayname
        if self.is_langpack_admin():
            self.adminlabel = 'Request a full language pack export of %s' % (
                self.displayname)
        else:
            self.adminlabel = 'Settings for language packs'


    @cachedproperty
    def unused_language_packs(self):
        unused_language_packs = helpers.shortlist(self.context.language_packs)

        if self.context.language_pack_base is not None:
            unused_language_packs.remove(self.context.language_pack_base)
        if self.context.language_pack_delta is not None:
            unused_language_packs.remove(self.context.language_pack_delta)
        if self.context.language_pack_proposed is not None:
            unused_language_packs.remove(self.context.language_pack_proposed)

        return unused_language_packs

    def _request_full_export(self):
        if (self.old_request_value !=
            self.context.language_pack_full_export_requested):
            # There are changes.
            if self.context.language_pack_full_export_requested:
                self.request.response.addInfoNotification(
                    "Your request has been noted. Next language pack export "
                    "will include all available translations.")
            else:
                self.request.response.addInfoNotification(
                    "Your request has been noted. Next language pack "
                    "export will be made relative to the current base "
                    "language pack.")
        else:
            self.request.response.addInfoNotification(
                "You didn't change anything.")

    @action("Change Settings", condition=is_translations_admin)
    def change_action(self, action, data):
        if ('language_pack_base' in data and
            data['language_pack_base'] != self.context.language_pack_base):
            # language_pack_base changed, the delta one must be invalidated.
            data['language_pack_delta'] = None
        self.updateContextFromData(data)
        self._request_full_export()
        self.request.response.addInfoNotification(
            'Your changes have been applied.')
        self.next_url = '%s/+language-packs' % canonical_url(self.context)

    @action("Request", condition=is_langpack_admin)
    def request_action(self, action, data):
        self.updateContextFromData(data)
        self._request_full_export()
        self.next_url = '/'.join(
            [canonical_url(self.context), '+language-packs'])


class DistroSeriesTemplatesView(LaunchpadView):
    """Show a list of all templates for the DistroSeries."""

    is_distroseries = True

    def iter_templates(self):
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(distroseries=self.context)

    def can_administer(self, template):
        return check_permission('launchpad.Admin', template)


class DistroSeriesView(LaunchpadView, TranslationsMixin):

    def initialize(self):
        self.displayname = '%s %s' % (
            self.context.distribution.displayname,
            self.context.version)

    def checkTranslationsViewable(self):
        """Check that these translations are visible to the current user.

        Launchpad admins, Translations admins, and users with admin
        rights on the `DistroSeries` are always allowed.  For others
        this delegates to `IDistroSeries.checkTranslationsViewable`,
        which raises `TranslationUnavailable` if the translations are
        set to be hidden.

        :return: Returns normally if this series' translations are
            viewable to the current user.
        :raise TranslationUnavailable: if this series' translations are
            hidden and the user is not one of the limited caste that is
            allowed to access them.
        """
        if check_permission('launchpad.Admin', self.context):
            # Anyone with admin rights on this series passes.  This
            # includes Launchpad admins.
            return

        user = self.user
        experts = getUtility(ILaunchpadCelebrities).rosetta_experts
        if user is not None and user.inTeam(experts):
            # Translations admins also pass.
            return

        # Everyone else passes only if translations are viewable to the
        # public.
        self.context.checkTranslationsViewable()

    def distroserieslanguages(self):
        """Produces a list containing a DistroSeriesLanguage object for
        each language this distro has been translated into, and for each
        of the user's preferred languages. Where the series has no
        DistroSeriesLanguage for that language, we use a
        DummyDistroSeriesLanguage.
        """

        # find the existing DRLanguages
        distroserieslangs = list(self.context.distroserieslanguages)

        # make a set of the existing languages
        existing_languages = set([drl.language for drl in distroserieslangs])

        # find all the preferred languages which are not in the set of
        # existing languages, and add a dummydistroserieslanguage for each
        # of them
        distroserieslangset = getUtility(IDistroSeriesLanguageSet)
        for lang in self.translatable_languages:
            if lang not in existing_languages:
                distroserieslang = distroserieslangset.getDummy(
                    self.context, lang)
                distroserieslangs.append(distroserieslang)

        return sorted(distroserieslangs, key=lambda a: a.language.englishname)

    @property
    def potemplates(self):
        return list(self.context.getCurrentTranslationTemplates())


class DistroSeriesTranslationsMenu(NavigationMenu):

    usedfor = IDistroSeries
    facet = 'translations'
    links = [
        'translations', 'templates', 'admin', 'language_packs', 'imports']

    def translations(self):
        return Link('', 'Overview')

    def imports(self):
        return Link('+imports', 'Import queue')

    @enabled_with_permission('launchpad.TranslationsAdmin')
    def admin(self):
        return Link('+admin', 'Settings')

    @enabled_with_permission('launchpad.Edit')
    def templates(self):
        return Link('+templates', 'Templates')

    def language_packs(self):
        return Link('+language-packs', 'Language packs')

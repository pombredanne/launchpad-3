# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser code for Language table."""

__metaclass__ = type
__all__ = [
    'LanguageAddView',
    'LanguageAdminView',
    'LanguageSetBreadcrumb',
    'LanguageSetContextMenu',
    'LanguageSetNavigation',
    'LanguageSetView',
    'LanguageView',
    ]

from zope.lifecycleevent import ObjectCreatedEvent
from zope.component import getUtility
from zope.event import notify
from zope.app.form.browser import TextWidget
from zope.interface import Interface
from zope.schema import TextLine

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp import (
    action, canonical_url, ContextMenu, custom_widget,
    enabled_with_permission, GetitemNavigation, LaunchpadEditFormView,
    LaunchpadFormView, LaunchpadView, Link, NavigationMenu)
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.tales import LanguageFormatterAPI
from lp.services.worlddata.interfaces.language import ILanguage, ILanguageSet
from lp.translations.interfaces.translationsperson import (
    ITranslationsPerson)
from lp.translations.browser.translations import TranslationsMixin
from lp.translations.utilities.pluralforms import make_friendly_plural_forms
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities

from canonical.widgets import LabeledMultiCheckBoxWidget


def describe_language(language):
    """Return full name for `language`."""
    englishname = language.englishname
    if language.nativename:
        return "%s (%s)" % (englishname, language.nativename)
    else:
        return englishname


class LanguageBreadcrumb(Breadcrumb):
    """`Breadcrumb` for `ILanguage`."""
    @property
    def text(self):
        return self.context.englishname


class LanguageSetNavigation(GetitemNavigation):
    usedfor = ILanguageSet


class LanguageSetBreadcrumb(Breadcrumb):
    """`Breadcrumb` for `ILanguageSet`."""
    text = u"Languages"


class LanguageSetContextMenu(ContextMenu):
    usedfor = ILanguageSet
    links = ['add']

    @enabled_with_permission('launchpad.Admin')
    def add(self):
        text = 'Add Language'
        return Link('+add', text, icon='add')


class LanguageNavigationMenu(NavigationMenu):
    usedfor = ILanguage
    facet = 'translations'
    links = ['administer']

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')


def _format_language(language):
    """Format a language as a link."""
    return LanguageFormatterAPI(language).link(None)


class ILanguageSetSearch(Interface):
    """The collection of languages."""

    search_lang = TextLine(
        title=u'Name of the language to search for.',
        required=True)

class LanguageSetView(LaunchpadFormView):
    """View class to render main ILanguageSet page."""
    label = "Languages in Launchpad"
    page_title = "Languages"

    schema = ILanguageSetSearch

    custom_widget('search_lang', TextWidget, displayWidth=30)

    def initialize(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.initialize(self)

        self.language_search = None

        search_lang_widget = self.widgets.get('search_lang')
        if (search_lang_widget is not None and
            search_lang_widget.hasValidInput()):
            self.language_search = search_lang_widget.getInputValue()
        self.search_requested = self.language_search is not None

    @cachedproperty
    def search_results(self):
        return self.context.search(text=self.language_search)

    @cachedproperty
    def search_matches(self):
        if self.search_results is not None:
            return self.search_results.count()
        else:
            return 0

    @cachedproperty
    def user_languages(self):
        """The user's preferred languages, or English if none are set."""
        languages = list(self.user.languages)
        if len(languages) == 0:
            languages = [getUtility(ILaunchpadCelebrities).english]
        return ", ".join(map(_format_language, languages))


# There is no easy way to remove an ILanguage from the database due all the
# dependencies that ILanguage would have. That's the reason why we don't have
# such functionality here.
class LanguageAddView(LaunchpadFormView):
    """View to handle ILanguage creation form."""

    rootsite = 'translations'

    schema = ILanguage
    field_names = ['code', 'englishname', 'nativename', 'pluralforms',
                   'pluralexpression', 'visible', 'direction']
    language = None

    page_title = "Register a language"
    label = "Register a language in Launchpad"

    @action('Add', name='add')
    def add_action(self, action, data):
        """Create the new Language from the form details."""
        self.language = getUtility(ILanguageSet).createLanguage(
            code=data['code'],
            englishname=data['englishname'],
            nativename=data['nativename'],
            pluralforms=data['pluralforms'],
            pluralexpression=data['pluralexpression'],
            visible=data['visible'],
            direction=data['direction'])
        notify(ObjectCreatedEvent(self.language))

    @property
    def cancel_url(self):
        """See LaunchpadFormView."""
        return canonical_url(self.context, rootsite=self.rootsite)

    @property
    def next_url(self):
        assert self.language is not None, 'No language has been created'
        return canonical_url(self.language, rootsite=self.rootsite)

    def validate(self, data):
        # XXX CarlosPerelloMarin 2007-04-04 bug=102898:
        # Pluralform expression should be validated.
        new_code = data.get('code')
        language_set = getUtility(ILanguageSet)
        if language_set.getLanguageByCode(new_code) is not None:
            self.setFieldError(
                'code', 'There is already a language with that code.')


class LanguageView(TranslationsMixin, LaunchpadView):
    """View class to render main ILanguage page."""

    @property
    def page_title(self):
        return self.context.englishname

    @property
    def label(self):
        return "%s in Launchpad" % self.language_name

    @cachedproperty
    def language_name(self):
        return describe_language(self.context)

    @cachedproperty
    def translation_teams(self):
        translation_teams = []
        for translation_team in self.context.translation_teams:
            # translation_team would be either a person or a team.
            translation_teams.append({
                'expert': translation_team,
                'groups': ITranslationsPerson(
                    translation_team).translation_groups,
                })
        return translation_teams

    @property
    def top_contributors(self):
        """
        Get top 20 contributors for a language.

        Instead of merged account, show the merged target account.
        """
        translators = []
        for translator in reversed(list(self.context.translators)):
            # Get only the top 20 contributors
            if (len(translators) >= 20):
                break

            # For merged account add the target account
            if translator_iter.merged != None:
                translator_target = translator.merged
            else:
                translator_target = translator

            # Add translator only if it was not previouly added as a
            # merged account
            if translator_target not in translators:
                translators.append(translator_target)

        return translators

    @property
    def friendly_plural_forms(self):
        """Formats the plural forms' example list.

        It takes the list of examples for each plural form and transforms in a
        comma separated list to be displayed.
        """
        pluralforms_list = make_friendly_plural_forms(
                self.context.pluralexpression, self.context.pluralforms)

        for item in pluralforms_list:
            examples = ", ".join(map(str, item['examples']))
            if len(item['examples']) != 1:
                examples += "..."
            else:
                examples += "."
            item['examples'] = examples

        return pluralforms_list

    @property
    def add_question_url(self):
        rosetta = getUtility(ILaunchpadCelebrities).lp_translations
        return canonical_url(
            rosetta,
            view_name='+addquestion',
            rootsite='answers')

class LanguageAdminView(LaunchpadEditFormView):
    """Handle an admin form submission."""

    rootsite = 'translations'

    schema = ILanguage

    custom_widget('countries', LabeledMultiCheckBoxWidget,
                  orientation='vertical')

    field_names = ['code', 'englishname', 'nativename', 'pluralforms',
                   'pluralexpression', 'visible', 'direction', 'countries']

    page_title = "Change details"

    @property
    def label(self):
        """The form label"""
        return "Edit %s in Launchpad" % describe_language(self.context)

    @property
    def cancel_url(self):
        """See LaunchpadFormView."""
        return canonical_url(self.context, rootsite=self.rootsite)

    @property
    def next_url(self):
        return canonical_url(self.context, rootsite=self.rootsite)

    @action("Admin Language", name="admin")
    def admin_action(self, action, data):
        self.updateContextFromData(data)

    def validate(self, data):
        new_code = data.get('code')
        if new_code == self.context.code:
            # The code didn't change.
            return

        language_set = getUtility(ILanguageSet)
        if language_set.getLanguageByCode(new_code) is not None:
            self.setFieldError(
                'code', 'There is already a language with that code.')


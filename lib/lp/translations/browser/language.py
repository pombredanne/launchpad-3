# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser code for Language table."""

__metaclass__ = type
__all__ = [
    'LanguageAddView',
    'LanguageAdminView',
    'LanguageSetContextMenu',
    'LanguageSetNavigation',
    'LanguageSetView',
    'LanguageView',
    ]

from zope.lifecycleevent import ObjectCreatedEvent
from zope.component import getUtility
from zope.event import notify

from canonical.cachedproperty import cachedproperty
from lp.services.worlddata.interfaces.language import ILanguage, ILanguageSet
from lp.translations.interfaces.translationsperson import (
    ITranslationsPerson)
from lp.translations.browser.translations import TranslationsMixin
from canonical.launchpad.webapp import (
    GetitemNavigation, LaunchpadView, LaunchpadFormView,
    LaunchpadEditFormView, action, canonical_url, ContextMenu, NavigationMenu,
    enabled_with_permission, Link, custom_widget)
from lp.translations.utilities.pluralforms import make_friendly_plural_forms

from canonical.widgets import LabeledMultiCheckBoxWidget

class LanguageSetNavigation(GetitemNavigation):
    usedfor = ILanguageSet


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

class LanguageSetView:
    """View class to render main ILanguageSet page."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        form = self.request.form
        self.language_search = form.get('language_search')
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
    def page_title(self):
        """Sets the page title."""
        return 'Add a new language to Launchpad'

    @property
    def label(self):
        """The form label."""
        return 'Register a language in Launchpad'

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

    @cachedproperty
    def language_name(self):
        if self.context.nativename is None:
            return self.context.englishname
        else:
            return self.context.nativename

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

    def getTopContributors(self):
        return self.context.translators[:20]

    @property
    def friendlypluralforms(self):
        """Formats the plural forms' example list.

        It takes the list of examples for each plural form and transforms in a
        comma separated list to be displayed.
        """
        pluralforms_list = make_friendly_plural_forms(
                self.context.pluralexpression, self.context.pluralforms)

        for item in pluralforms_list:
            examples = ", ".join(map(str, item['examples']))
            if len(item['examples']) != 1:
                examples += ", ..."
            else:
                examples += "."
            item['examples'] = examples

        return pluralforms_list


class LanguageAdminView(LaunchpadEditFormView):
    """Handle an admin form submission."""

    rootsite = 'translations'

    schema = ILanguage

    custom_widget('countries', LabeledMultiCheckBoxWidget,
                  orientation='vertical')

    field_names = ['code', 'englishname', 'nativename', 'pluralforms',
                   'pluralexpression', 'visible', 'direction', 'countries']

    @property
    def page_title(self):
        return "Edit %s" % self.context.displayname

    @property
    def label(self):
        """The form label"""
        if self.context.nativename is None:
            name = self.context.englishname
        else:
            name = self.context.nativename
        return "Edit %s in Launchpad" % name

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


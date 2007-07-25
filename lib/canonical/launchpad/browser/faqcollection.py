# Copyright 2007 Canonical Ltd.  All rights reserved.

"""IFAQCollection browser views."""

__metaclass__ = type

__all__ = [
    'FAQCollectionMenu',
    'SearchFAQsView',
    ]

from urllib import urlencode

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IFAQCollection, ISearchFAQsForm, QUESTION_STATUS_DEFAULT_SEARCH,
    QuestionSort)
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, LaunchpadFormView, Link,
    safe_action)
from canonical.launchpad.webapp.batching import BatchNavigator


class FAQCollectionMenu(ApplicationMenu):
    """Base menu definition for `IFAQCollection`."""

    usedfor = IFAQCollection
    facet = 'answers'
    links = ['list_all']

    def list_all(self):
        """Return a Link to list all FAQs."""
        # We adapt to IFAQCollection so that the link can be used
        # on objects which don't provide `IFAQCollection` directly, but for
        # which an adapter exists that gives the proper context.
        collection = IFAQCollection(self.context)
        url = canonical_url(collection, rootsite='answers') + '/+faqs'
        return Link(url, 'List all FAQs')


class SearchFAQsView(LaunchpadFormView):
    """View to list and search FAQs."""

    schema = ISearchFAQsForm

    # This attribute contains the search_text to use.
    search_text = None

    # This attribute is updated to the number of matching questions when
    # the user does a search.
    matching_questions_count = 0

    @property
    def heading(self):
        """Return the heading that should be used for the listing."""
        replacements = dict(
            displayname=self.context.displayname,
            search_text=self.search_text)
        if self.search_text:
            return _(u'FAQs matching \u201c${search_text}\u201d for '
                     u'$displayname', mapping=replacements)
        else:
            return _('FAQs for $displayname', mapping=replacements)

    @property
    def empty_listing_message(self):
        """Return the message to render when there are no FAQs to display."""
        replacements = dict(
            displayname=self.context.displayname,
            search_text=self.search_text)
        if self.search_text:
            return _(u'There are no FAQs for $displayname matching '
                     u'\u201c${search_text}\u201d.', mapping=replacements)
        else:
            return _('There are no FAQs for $displayname.',
                     mapping=replacements)

    def getMatchingFAQs(self):
        """Return a BatchNavigator of the matching FAQs."""
        faqs = self.context.searchFAQs(search_text=self.search_text)
        return BatchNavigator(faqs, self.request)

    @safe_action
    @action(_('Search'), name='search')
    def search_action(self, action, data):
        """Filter the search results by keywords."""
        self.search_text = data.get('search_text', None)
        if self.search_text:
            matching_questions = self.context.searchQuestions(
                search_text=self.search_text)
            self.matching_questions_count = matching_questions.count()

    @property
    def matching_questions_url(self):
        """Return the URL to the questions matching the same keywords."""
        return canonical_url(self.context) + '/+questions?' + urlencode(
            {'field.status': [
                status.title for status in QUESTION_STATUS_DEFAULT_SEARCH],
             'field.search_text': self.search_text,
             'field.actions.search': 'Search',
             'field.sort' : QuestionSort.RELEVANCY.title,
             'field.language-empty-marker': 1}, doseq=True)

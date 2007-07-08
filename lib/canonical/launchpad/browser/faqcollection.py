# Copyright 2007 Canonical Ltd.  All rights reserved.

"""IFAQCollection browser views."""

__metaclass__ = type

__all__ = [
    'FAQCollectionMenu',
    'SearchFAQsBaseView',
    ]

from canonical.launchpad import _
from canonical.launchpad.interfaces import IFAQCollection, ISearchFAQsForm
from canonical.launchpad.webapp import ContextMenu, LaunchpadFormView, Link
from canonical.launchpad.webapp.batching import BatchNavigator


class FAQCollectionMenu(ContextMenu):
    """Base menu definition for FAQCollection."""

    usedfor = IFAQCollection
    facet = 'answers'
    links = ['list_all']

    def list_all(self):
        """Return a Link to list all FAQs."""
        return Link('+faqs', 'List all FAQs')


class SearchFAQsBaseView(LaunchpadFormView):
    """View to list and search FAQs."""

    schema = ISearchFAQsForm

    @property
    def heading(self):
        """Return the heading that should be used for the listing."""
        return _('FAQs for $displayname',
                 mapping=dict(displayname=self.context.displayname))

    def getMatchingFAQs(self):
        """Return a BatchNavigator of the matching FAQs."""
        return BatchNavigator(self.context.searchFAQs(), self.request)

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`IFAQ` browser views."""

__metaclass__ = type

__all__ = [
    'FAQNavigationMenu',
    'FAQEditView',
    ]

from canonical.launchpad import _
from canonical.launchpad.webapp import (
    action, NavigationMenu, canonical_url, enabled_with_permission,
    LaunchpadEditFormView, Link)

from lp.answers.browser.faqcollection import FAQCollectionMenu
from lp.answers.interfaces.faq import IFAQ


class FAQNavigationMenu(NavigationMenu):
    """Context menu of actions that can be performed upon a FAQ."""

    usedfor = IFAQ
    title = 'Edit FAQ'
    facet = 'answers'
    links = ['edit', 'list_all']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        """Return a Link to the edit view."""
        return Link('+edit', _('Edit FAQ'), icon='edit')

    def list_all(self):
        """Return a Link to list all FAQs."""
        # We adapt to IFAQCollection so that the link can be used
        # on objects which don't provide `IFAQCollection` directly, but for
        # which an adapter exists that gives the proper context.
        collection = IFAQCollection(self.context)
        url = canonical_url(collection, rootsite='answers') + '/+faqs'
        return Link(url, 'List all FAQs', icon='info')


class FAQEditView(LaunchpadEditFormView):
    """View to change the FAQ details."""

    schema = IFAQ
    label = _('Edit FAQ')
    field_names = ["title", "keywords", "content"]

    @property
    def page_title(self):
        return 'Edit FAQ #%s details' % self.context.id

    @action(_('Save'), name="save")
    def save_action(self, action, data):
        """Update the FAQ details."""
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)

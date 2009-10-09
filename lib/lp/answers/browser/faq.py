# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`IFAQ` browser views."""

__metaclass__ = type

__all__ = [
    'FAQNavigationMenu',
    'FAQEditView',
    'FAQView',
    ]

from canonical.launchpad import _
from canonical.launchpad.webapp import (
    action, NavigationMenu, canonical_url, enabled_with_permission,
    LaunchpadView, LaunchpadEditFormView, Link)

from lp.answers.browser.faqcollection import FAQCollectionMenu
from lp.answers.interfaces.faq import IFAQ
from lp.answers.interfaces.faqcollection import IFAQCollection


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


class FAQView(LaunchpadView):
    """View for the FAQ index."""

    __used_for__ = IFAQ

    @property
    def page_title(self):
        return '%s FAQ #%d: "%s"' % (
            self.context.target.displayname,
            self.context.id,
            self.context.title)

    label = page_title


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

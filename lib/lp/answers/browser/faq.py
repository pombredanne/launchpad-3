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
    links = ['edit']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        """Return a Link to the edit view."""
        return Link('+edit', _('Edit FAQ'), icon='edit')


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

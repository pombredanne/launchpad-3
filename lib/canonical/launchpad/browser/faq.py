# Copyright 2007 Canonical Ltd.  All rights reserved.

"""`IFAQ` browser views."""

__metaclass__ = type

__all__ = [
    'FAQContextMenu',
    'FAQEditView',
    'FAQStructuralObjectPresentation',
    'FAQView',
    ]

from canonical.launchpad import _
from canonical.launchpad.browser.faqcollection import FAQCollectionMenu
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.interfaces import IFAQ
from canonical.launchpad.webapp import (
    action, canonical_url, enabled_with_permission, LaunchpadEditFormView,
    LaunchpadView, Link)


class FAQContextMenu(FAQCollectionMenu):
    """Context menu of actions that can be performed upon a FAQ."""
    usedfor = IFAQ
    links = FAQCollectionMenu.links + [
        'edit',
        ]

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        """Return a Link to the edit view."""
        return Link('+edit', _('Edit FAQ'))


class FAQEditView(LaunchpadEditFormView):
    """View to change the FAQ details."""

    schema = IFAQ
    label = _('Edit FAQ')
    field_names = ["title", "keywords", "content"]

    @action(_('Save'), name="save")
    def save_action(self, action, data):
        """Update the FAQ details."""
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class FAQStructuralObjectPresentation(StructuralObjectPresentation):
    """Provides the structural heading for `IFAQ`."""

    def getMainHeading(self):
        """See `IStructuralHeaderPresentation`."""
        faq = self.context
        return _('FAQ #${id} in ${target}',
                 mapping=dict(
                    id=faq.id, target=faq.target.displayname))

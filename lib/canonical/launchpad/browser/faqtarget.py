# Copyright 2007 Canonical Ltd.  All rights reserved.

"""`IFAQTarget` browser views."""

__metaclass__ = type

__all__ = [
    'FAQTargetNavigationMixin',
    'FAQCreateView',
    ]

from canonical.launchpad import _
from canonical.launchpad.interfaces import IFAQ
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadFormView, stepthrough)
from canonical.launchpad.webapp.interfaces import NotFoundError
from canonical.widgets import TokensTextWidget


class FAQTargetNavigationMixin:
    """Navigation mixin for `IFAQTarget`."""

    @stepthrough('+faq')
    def traverse_faq(self, name):
        """Return the FAQ by ID."""
        try:
            id_ = int(name)
        except ValueError:
            return NotFoundError
        return self.context.getFAQ(id_)


class FAQCreateView(LaunchpadFormView):
    """A view to create a new FAQ."""

    schema = IFAQ
    label = _('Create a new FAQ')
    field_names = ['title', 'keywords', 'content']

    custom_widget('keywords', TokensTextWidget)

    @action(_('Create'), name='create')
    def create__action(self, action, data):
        """Creates the FAQ."""
        faq = self.context.newFAQ(
            self.user, data['title'], data['content'],
            keywords=data['keywords'])
        self.next_url = canonical_url(faq)


# Copyright 2007 Canonical Ltd.  All rights reserved.

"""`IFAQTarget` browser views."""

__metaclass__ = type

__all__ = [
    'FAQTargetNavigationMixin',
    ]

from canonical.launchpad.webapp import stepthrough
from canonical.launchpad.webapp.interfaces import NotFoundError


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


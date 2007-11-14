# Copyright 2007 Canonical Ltd.  All rights reserved.

"""`IFAQTarget` browser views."""

__metaclass__ = type

__all__ = [
    'FAQTargetNavigationMixin',
    ]

from canonical.launchpad.webapp import stepthrough


class FAQTargetNavigationMixin:
    """Navigation mixin for `IFAQTarget`."""

    @stepthrough('+faq')
    def traverse_faq(self, name):
        """Return the FAQ by ID."""
        return self.context.getFAQ(name)



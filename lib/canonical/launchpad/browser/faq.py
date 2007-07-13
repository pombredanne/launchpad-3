# Copyright 2007 Canonical Ltd.  All rights reserved.

"""`IFAQ` browser views."""

__metaclass__ = type

__all__ = [
    'FAQStructuralObjectPresentation',
    ]

from canonical.launchpad import _
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation


class FAQStructuralObjectPresentation(StructuralObjectPresentation):
    """Provides the structural heading for `IFAQ`."""

    def getMainHeading(self):
        """See `IStructuralHeaderPresentation`."""
        faq = self.context
        return _('FAQ #${id} in ${target}',
                 mapping=dict(
                    id=faq.id, target=faq.target.displayname))



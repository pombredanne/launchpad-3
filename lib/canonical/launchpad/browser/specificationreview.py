# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationReview."""

__metaclass__ = type

from zope.app.form.browser.add import AddView

from canonical.launchpad.interfaces import ISpecificationReview

from canonical.launchpad.webapp import canonical_url


__all__ = [
    'SpecificationReviewAddView',
    ]

class SpecificationReviewAddView(AddView):

    def create(self, reviewer, requestor, queuemsg=None):
        return self.context.queue(reviewer, requestor, queuemsg)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)



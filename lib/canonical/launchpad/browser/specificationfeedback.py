# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationFeedback."""

__metaclass__ = type

from zope.app.form.browser.add import AddView

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ISpecificationFeedback, ILaunchBag)

from canonical.launchpad.webapp import canonical_url, GeneralFormView


__all__ = [
    'SpecificationFeedbackAddView',
    'SpecificationFeedbackClearingView',
    ]


class SpecificationFeedbackAddView(AddView):

    def create(self, reviewer, requestor, queuemsg=None):
        return self.context.queue(reviewer, requestor, queuemsg)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


class SpecificationFeedbackClearingView(GeneralFormView):

    def feedbackrequests(self):
        """Return the feedback requests on this spec which have been made of
        this user."""
        if self.user is None:
            return None
        return self.context.getFeedbackRequests(self.user)

    @property
    def user(self):
        """Return the Launchpad person who is logged in."""
        return getUtility(ILaunchBag).user

    def process(self):
        import pdb; pdb.set_trace()
        return 'Done!'



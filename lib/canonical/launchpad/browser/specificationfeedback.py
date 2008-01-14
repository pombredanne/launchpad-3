# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationFeedback."""

__metaclass__ = type

from zope.app.form.interfaces import WidgetsError
from zope.app.form.browser.add import AddView

from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    ISpecificationFeedback, ILaunchBag, IPersonSet)

from canonical.launchpad.webapp import canonical_url


__all__ = [
    'SpecificationFeedbackAddView',
    'SpecificationFeedbackClearingView',
    ]


class SpecificationFeedbackAddView(AddView):

    def __init__(self, context, request):
        AddView.__init__(self, context, request)
        self.top_of_page_errors = []

    def valid_feedback_request(self, spec, reviewer, requester):
        for request in spec.getFeedbackRequests(reviewer):
            if request.requester == requester:
                return False
        return True

    def create(self, reviewer, requester, queuemsg=None):
        if reviewer == requester:
            self.top_of_page_errors.append(_(
                "You can't request feedback from yourself"))
        elif not self.valid_feedback_request(self.context, reviewer, requester):
            self.top_of_page_errors.append(_(
                "You've already requested feedback from %s"
                % reviewer.displayname))
        if self.top_of_page_errors:
            raise WidgetsError(self.top_of_page_errors)
        return self.context.queue(reviewer, requester, queuemsg)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


class SpecificationFeedbackClearingView:

    def __init__(self, context, request):
        """A custom little view class to process the results of this unusual
        page. It is unusual because we want to display multiple objects with
        checkboxes, then process the selected items, which is not the usual
        add/edit metaphor."""
        self.context = context
        self.request = request
        self.process_status = None

    @property
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

    def process_form(self):
        """Largely copied from webapp/generalform.py, without the
        schema processing bits because we are not rendering the form in the
        usual way. Instead, we are creating our own form in the page
        template and interpreting it here."""

        if self.process_status is not None:
            # We've been called before. Just return the status we previously
            # computed.
            return self.process_status

        if 'cancel' in self.request:
            self.process_status = 'Cancelled'
            self.request.response.redirect(canonical_url(self.context))
            return self.process_status

        if "FORM_SUBMIT" not in self.request:
            self.process_status = ''
            return self.process_status

        if self.request.method == 'POST':
            if 'feedbackrequest' not in self.request:
                self.process_status = ('Please select feedback queue items '
                                       'to clear.')
                return self.process_status

        clearedreqs = self.request['feedbackrequest']
        if isinstance(clearedreqs, unicode):
            # only a single item was selected, but we want to deal with a
            # list for the general case, so convert it to a list
            clearedreqs = [clearedreqs,]

        queue_length = len(self.context.getFeedbackRequests(self.user))
        number_cleared = 0
        msg = 'Cleared requests from: '
        for clearedreq in clearedreqs:
            requester = getUtility(IPersonSet).getByName(clearedreq)
            if requester is not None:
                self.context.unqueue(self.user, requester)
                if number_cleared > 0:
                    msg += ', '
                msg += requester.browsername
                number_cleared += 1

        self.process_status = msg

        if number_cleared == queue_length:
            # they are all done, so redirect back to the spec
            self.request.response.redirect(canonical_url(self.context))

        return self.process_status



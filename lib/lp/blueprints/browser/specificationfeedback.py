# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views for SpecificationFeedback."""

__metaclass__ = type

from zope.app.form.browser import TextAreaWidget

from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.registry.interfaces.person import IPersonSet
from canonical.launchpad.webapp import action, canonical_url, custom_widget
from canonical.launchpad.webapp.launchpadform import LaunchpadFormView
from lp.blueprints.interfaces.specificationfeedback import (
    ISpecificationFeedback)


__all__ = [
    'SpecificationFeedbackAddView',
    'SpecificationFeedbackClearingView',
    ]


class SpecificationFeedbackAddView(LaunchpadFormView):

    schema = ISpecificationFeedback

    field_names = [
        'reviewer', 'queuemsg',
        ]

    custom_widget('queuemsg', TextAreaWidget, height=5)

    @property
    def label(self):
        return "Request feedback on specification"

    @property
    def page_title(self):
        return self.label

    def validate(self, data):
        reviewer = data.get('reviewer')
        requester = self.user
        for request in self.context.getFeedbackRequests(reviewer):
            if request.requester == requester:
                self.addError("You've already requested feedback from %s"
                    % reviewer.displayname)
        if reviewer == requester:
            self.addError("You can't request feedback from yourself")

    @action(_("Add"), name="create")
    def create_action(self, action, data):
        reviewer = data.get('reviewer')
        requester = self.user
        queuemsg = data.get('queuemsg')
        return self.context.queue(reviewer, requester, queuemsg)

    @property
    def next_url(self):
        return canonical_url(self.context)

    @property
    def cancel_url(self):
        return self.next_url


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

        queue_length = self.context.getFeedbackRequests(self.user).count()
        number_cleared = 0
        msg = 'Cleared requests from: '
        for clearedreq in clearedreqs:
            requester = getUtility(IPersonSet).getByName(clearedreq)
            if requester is not None:
                self.context.unqueue(self.user, requester)
                if number_cleared > 0:
                    msg += ', '
                msg += requester.displayname
                number_cleared += 1

        self.process_status = msg

        if number_cleared == queue_length:
            # they are all done, so redirect back to the spec
            self.request.response.redirect(canonical_url(self.context))

        return self.process_status


# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views for SpecificationFeedback."""

__metaclass__ = type

from zope.app.form.interfaces import WidgetsError
from zope.app.form.browser.add import AddView

from zope.component import getUtility
from zope.interface import Interface

from canonical.launchpad import _
from canonical.launchpad.helpers import english_list
from lp.registry.interfaces.person import IPersonSet
from canonical.launchpad.webapp import (
    LaunchpadFormView, action, canonical_url)


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
        elif not self.valid_feedback_request(
            self.context, reviewer, requester):
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


class SpecificationFeedbackClearingView(LaunchpadFormView):

    schema = Interface
    field_names = []

    @property
    def label(self):
        return _('Give feedback on this blueprint')

    @property
    def requests(self):
        """Return the feedback requests made of this user."""
        if self.user is None:
            return None
        return self.context.getFeedbackRequests(self.user)

    @action(_('Save changes'), name='save')
    def save_action(self, action, data):
        names = self.request.form_ng.getAll('name')
        if len(names) == 0:
            self.request.response.addNotification(
                'Please select feedback queue items to clear.')
        else:
            cleared_from = []
            for name in names:
                requester = getUtility(IPersonSet).getByName(name)
                if requester is not None:
                    self.context.unqueue(self.user, requester)
                    cleared_from.append(requester.displayname)
            self.request.response.addNotification(
                'Cleared requests from: %s' % english_list(cleared_from))

    @property
    def next_url(self):
        if self.context.getFeedbackRequests(self.user).count() == 0:
            # No more queue items to process; return to the spec.
            return canonical_url(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)

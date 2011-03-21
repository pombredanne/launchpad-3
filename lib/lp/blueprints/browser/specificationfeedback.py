# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views for SpecificationFeedback."""

__metaclass__ = type

from zope.app.form.browser import TextAreaWidget
from zope.component import getUtility
from zope.interface import Interface

from canonical.launchpad import _
from canonical.launchpad.helpers import english_list
from canonical.launchpad.webapp import (
    canonical_url,
    )
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadFormView,
    )
from lp.blueprints.interfaces.specificationfeedback import (
    ISpecificationFeedback,
    )
from lp.registry.interfaces.person import IPersonSet


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

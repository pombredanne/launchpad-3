# Copyright 2006-2009 Canonical Ltd.  All rights reserved.

"""Views for linking bugs and questions."""

__metaclass__ = type
__all__ = []


from zope.event import notify

from canonical.launchpad import _
from zope.interface import providedBy

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot

from canonical.launchpad.interfaces.bug import CreateBugParams,  IBug
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.launchpadform import action, LaunchpadFormView

class QuestionMakeBugView(LaunchpadFormView):
    """Browser class for adding a bug from a question."""

    schema = IBug

    field_names = ['title', 'description']

    def initialize(self):
        """Initialize the view when a Bug may be reported for the Question."""
        question = self.context
        if question.bugs:
            # we can't make a bug when we have linked bugs
            self.request.response.addErrorNotification(
                _('You cannot create a bug report from a question'
                  'that already has bugs linked to it.'))
            self.request.response.redirect(canonical_url(question))
            return
        LaunchpadFormView.initialize(self)

    @property
    def initial_values(self):
        """Return the initial form values."""
        question = self.context
        return {'title': '',
                'description': question.description}

    @action(_('Create Bug Report'), name='create')
    def create_action(self, action, data):
        """Create a Bug from a Question."""
        question = self.context

        unmodifed_question = Snapshot(
            question, providing=providedBy(question))
        params = CreateBugParams(
            owner=self.user, title=data['title'], comment=data['description'])
        bug = question.target.createBug(params)
        question.linkBug(bug)
        bug.subscribe(question.owner, self.user)
        bug_added_event = ObjectModifiedEvent(
            question, unmodifed_question, ['bugs'])
        notify(bug_added_event)
        self.request.response.addNotification(
            _('Thank you! Bug #$bugid created.', mapping={'bugid': bug.id}))
        self.next_url = canonical_url(bug)




# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views for linking bugs and questions."""

__metaclass__ = type
__all__ = []

from lp import _
from lp.app.browser.launchpadform import (
    action,
    LaunchpadFormView,
    )
from lp.bugs.interfaces.bug import (
    CreateBugParams,
    IBug,
    )
from lp.services.webapp.publisher import canonical_url
from lp.services.webapp.snapshot import notify_modified


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
    def page_title(self):
        return 'Create bug report based on question #%s' % self.context.id

    @property
    def label(self):
        return 'Create a bug based on a question'

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

        with notify_modified(question, ['bugs']):
            params = CreateBugParams(
                owner=self.user, title=data['title'],
                comment=data['description'])
            bug = question.target.createBug(params)
            question.linkBug(bug, user=self.user)
            bug.subscribe(question.owner, self.user)
        self.request.response.addNotification(
            _('Thank you! Bug #$bugid created.', mapping={'bugid': bug.id}))
        self.next_url = canonical_url(bug)

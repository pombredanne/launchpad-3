# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


"""Views, navigation and actions for CodeReviewVotes."""


__metaclass__ = type


from zope.interface import Interface

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView)


class ReassignSchema(Interface):

    reviewer = PublicPersonChoice( title=_('Reviewer'), required=True,
            description=_('A person who you want to review this.'),
            vocabulary='ValidPersonOrTeam')


class CodeReviewVoteReassign(LaunchpadFormView):

    schema = ReassignSchema

    @action('Reassign', name='reassign')
    def reassign_action(self, action, data):
        self.context.reviewer = data['reviewer']
        self.next_url = canonical_url(self.context.branch_merge_proposal)

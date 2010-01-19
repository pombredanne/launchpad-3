# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


"""Views, navigation and actions for CodeReviewVotes."""


__metaclass__ = type


from zope.interface import Interface
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView)


class ReassignSchema(Interface):
    """Schema to use when reassigning the reviewer for a requested review."""

    reviewer = PublicPersonChoice( title=_('Reviewer'), required=True,
            description=_('A person who you want to review this.'),
            vocabulary='ValidPersonOrTeam')


class CodeReviewVoteReassign(LaunchpadFormView):
    """View for reassinging the reviewer for a requested review."""

    schema = ReassignSchema

    page_title = label = 'Reassign review request'

    @action('Reassign', name='reassign')
    def reassign_action(self, action, data):
        """Use the form data to change the review request reviewer."""
        # XXX TimPenhey 2009-12-11 bug=495201
        # This should check for existing reviews by the reviewer, and have
        # the logic moved into the model code.
        removeSecurityProxy(self.context).reviewer = data['reviewer']
        self.next_url = canonical_url(self.context.branch_merge_proposal)

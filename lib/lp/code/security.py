# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Security adapters for the code module."""

__metaclass__ = type
__all__ = [
    'BranchSubscriptionEdit',
    'BranchSubscriptionView',
    ]

from canonical.launchpad.security import AuthorizationBase
from lp.code.interfaces.branchsubscription import IBranchSubscription


class BranchSubscriptionEdit(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBranchSubscription

    def checkAuthenticated(self, user):
        """Is the user able to edit a branch subscription?

        Any team member can edit a branch subscription for their team.
        Launchpad Admins can also edit any branch subscription.
        """
        return (user.inTeam(self.obj.person) or
                user.inTeam(self.obj.subscribed_by) or
                user.in_admin or
                user.in_bazaar_experts)


class BranchSubscriptionView(BranchSubscriptionEdit):
    permission = 'launchpad.View'



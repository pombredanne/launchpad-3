# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Security adapters for the bugs module."""

__metaclass__ = type
__all__ = []

from canonical.launchpad.interfaces.launchpad import IHasBug
from lp.services.messages.interfaces.message import IMessage
from lp.app.security import (
    AnonymousAuthorization,
    AuthorizationBase,
    ForwardedAuthorization,
    )
from lp.bugs.interfaces.bug import IBug
from lp.bugs.interfaces.bugattachment import IBugAttachment
from lp.bugs.interfaces.bugbranch import IBugBranch
from lp.bugs.interfaces.bugnomination import IBugNomination
from lp.bugs.interfaces.bugsubscription import IBugSubscription
from lp.bugs.interfaces.bugsubscriptionfilter import IBugSubscriptionFilter
from lp.bugs.interfaces.bugtracker import IBugTracker
from lp.bugs.interfaces.bugwatch import IBugWatch
from lp.bugs.interfaces.structuralsubscription import IStructuralSubscription


class EditBugNominationStatus(AuthorizationBase):
    permission = 'launchpad.Driver'
    usedfor = IBugNomination

    def checkAuthenticated(self, user):
        return self.obj.canApprove(user.person)


class EditBugTask(AuthorizationBase):
    """Permission checker for editing objects linked to a bug.

    Allow any logged-in user to edit objects linked to public
    bugs. Allow only explicit subscribers to edit objects linked to
    private bugs.
    """
    permission = 'launchpad.Edit'
    usedfor = IHasBug

    def checkAuthenticated(self, user):
        # Delegated entirely to the bug.
        return self.obj.bug.userCanView(user)


class PublicToAllOrPrivateToExplicitSubscribersForBugTask(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IHasBug

    def checkAuthenticated(self, user):
        return self.obj.bug.userCanView(user.person)

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.bug.private


class EditPublicByLoggedInUserAndPrivateByExplicitSubscribers(
    AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBug

    def checkAuthenticated(self, user):
        """Allow any logged in user to edit a public bug, and only
        explicit subscribers to edit private bugs. Any bug that can be
        seen can be edited.
        """
        return self.obj.userCanView(user)

    def checkUnauthenticated(self):
        """Never allow unauthenticated users to edit a bug."""
        return False


class PublicToAllOrPrivateToExplicitSubscribersForBug(AuthorizationBase):
    permission = 'launchpad.View'
    usedfor = IBug

    def checkAuthenticated(self, user):
        """Allow any user to see non-private bugs, but only explicit
        subscribers to see private bugs.
        """
        return self.obj.userCanView(user.person)

    def checkUnauthenticated(self):
        """Allow anonymous users to see non-private bugs only."""
        return not self.obj.private


class EditBugBranch(EditPublicByLoggedInUserAndPrivateByExplicitSubscribers):
    permission = 'launchpad.Edit'
    usedfor = IBugBranch

    def __init__(self, bug_branch):
        # The same permissions as for the BugBranch's bug should apply
        # to the BugBranch itself.
        super(EditBugBranch, self).__init__(bug_branch.bug)


class ViewBugAttachment(ForwardedAuthorization):
    """Security adapter for viewing a bug attachment.

    If the user is authorized to view the bug, he's allowed to view the
    attachment.
    """
    permission = 'launchpad.View'
    usedfor = IBugAttachment

    def __init__(self, bugattachment):
        super(ViewBugAttachment, self).__init__(bugattachment.bug)


class EditBugAttachment(ForwardedAuthorization):
    """Security adapter for editing a bug attachment.

    If the user is authorized to view the bug, he's allowed to edit the
    attachment.
    """
    permission = 'launchpad.Edit'
    usedfor = IBugAttachment

    def __init__(self, bugattachment):
        super(EditBugAttachment, self).__init__(bugattachment.bug)


class ViewBugSubscription(AnonymousAuthorization):

    usedfor = IBugSubscription


class EditBugSubscription(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBugSubscription

    def checkAuthenticated(self, user):
        """Check that a user may edit a subscription.

        A user may edit a subscription if:
         - They are the owner of the subscription.
         - They are the owner of the team that owns the subscription.
         - They are an admin of the team that owns the subscription.
        """
        if self.obj.person.isTeam():
            return (
                self.obj.person.teamowner == user.person or
                user.person in self.obj.person.adminmembers)
        else:
            return user.person == self.obj.person


class ViewBugMessage(AnonymousAuthorization):

    usedfor = IMessage


class SetBugCommentVisibility(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IBug

    def checkAuthenticated(self, user):
        """Admins and registry admins can set bug comment visibility."""
        return (user.in_admin or user.in_registry_experts)


class ViewBugTracker(AnonymousAuthorization):
    """Anyone can view a bug tracker."""
    usedfor = IBugTracker


class EditBugTracker(AuthorizationBase):
    permission = 'launchpad.Edit'
    usedfor = IBugTracker

    def checkAuthenticated(self, user):
        """Any logged-in user can edit a bug tracker."""
        return True


class AdminBugTracker(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IBugTracker

    def checkAuthenticated(self, user):
        return (
            user.in_janitor or
            user.in_admin or
            user.in_launchpad_developers)


class AdminBugWatch(AuthorizationBase):
    permission = 'launchpad.Admin'
    usedfor = IBugWatch

    def checkAuthenticated(self, user):
        return (
            user.in_admin or
            user.in_launchpad_developers)


class EditStructuralSubscription(AuthorizationBase):
    """Edit permissions for `IStructuralSubscription`."""
    permission = "launchpad.Edit"
    usedfor = IStructuralSubscription

    def checkAuthenticated(self, user):
        """Subscribers can edit their own structural subscriptions."""
        return user.inTeam(self.obj.subscriber)


class EditBugSubscriptionFilter(AuthorizationBase):
    """Bug subscription filters may only be modified by the subscriber."""
    permission = 'launchpad.Edit'
    usedfor = IBugSubscriptionFilter

    def checkAuthenticated(self, user):
        return (
            self.obj.structural_subscription is None or
            user.inTeam(self.obj.structural_subscription.subscriber))

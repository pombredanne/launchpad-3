# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Email code for the branch scanner."""

__metaclass__ = type
__all__ = [
    'BranchMailer',
    'send_tip_changed_emails',
    ]

from zope.component import adapter, getUtility

from canonical.codehosting.scanner import events
from canonical.config import config
from lp.code.interfaces.branchjob import (
    IRevisionsAddedJobSource, IRevisionMailJobSource)
from lp.code.interfaces.branchsubscription import (
    BranchSubscriptionNotificationLevel)


def subscribers_want_notification(db_branch):
    diff_levels = (
        BranchSubscriptionNotificationLevel.DIFFSONLY,
        BranchSubscriptionNotificationLevel.FULL)
    subscriptions = db_branch.getSubscriptionsByLevel(diff_levels)
    return subscriptions.count() > 0


class BranchMailer:
    """Handles mail notifications for changes to the code in a branch."""

    def __init__(self, db_branch):
        self.db_branch = db_branch
        self.subscribers_want_notification = False

    def initializeEmailQueue(self):
        """Create an email queue and determine whether to create diffs.

        In order to avoid sending emails when no one is interested in seeing
        them, we check all the branch subscriptions first, and decide here
        whether or not to generate the revision diffs as the branch is
        scanned.
        """
        self.subscribers_want_notification = subscribers_want_notification(
            self.db_branch)

    def generateEmailForRemovedRevisions(self, removed_history):
        """Notify subscribers of removed revisions.

        When the history is shortened, and email is sent that says this. This
        will never happen for a newly scanned branch, so not checking that
        here.
        """
        if not self.subscribers_want_notification:
            return
        number_removed = len(removed_history)
        if number_removed > 0:
            if number_removed == 1:
                contents = '1 revision was removed from the branch.'
            else:
                contents = ('%d revisions were removed from the branch.'
                            % number_removed)
            # No diff is associated with the removed email.
            job = getUtility(IRevisionMailJobSource).create(
                self.db_branch, revno='removed',
                from_address=config.canonical.noreply_from_address,
                body=contents, perform_diff=False, subject=None)


@adapter(events.TipChanged)
def send_tip_changed_emails(tip_changed):
    if not tip_changed.initial_scan:
        getUtility(IRevisionsAddedJobSource).create(
            tip_changed.db_branch, tip_changed.db_branch.last_scanned_id,
            tip_changed.bzr_branch.last_revision(),
            config.canonical.noreply_from_address)
    elif subscribers_want_notification(tip_changed.db_branch):
        revision_count = tip_changed.bzr_branch.revno()
        if revision_count == 1:
            revisions = '1 revision'
        else:
            revisions = '%d revisions' % revision_count
        message = ('First scan of the branch detected %s'
                   ' in the revision history of the branch.' %
                   revisions)
        job = getUtility(IRevisionMailJobSource).create(
            tip_changed.db_branch, 'initial',
            config.canonical.noreply_from_address, message, False, None)

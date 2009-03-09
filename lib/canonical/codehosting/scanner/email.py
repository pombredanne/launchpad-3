# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Email code for the branch scanner."""

__metaclass__ = type
__all__ = [
    'BranchMailer',
    ]

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import BranchSubscriptionNotificationLevel
from canonical.launchpad.interfaces.branchjob import IRevisionMailJobSource


class BranchMailer:
    """Handles mail notifications for changes to the code in a branch."""

    def __init__(self, trans_manager, db_branch):
        self.trans_manager = trans_manager
        self.db_branch = db_branch
        self.pending_emails = []
        self.subscribers_want_notification = False
        self.initial_scan = None
        self.email_from = config.canonical.noreply_from_address

    def initializeEmailQueue(self, initial_scan):
        """Create an email queue and determine whether to create diffs.

        In order to avoid sending emails when no one is interested in seeing
        them, we check all the branch subscriptions first, and decide here
        whether or not to generate the revision diffs as the branch is
        scanned.

        See XXX comment in `sendRevisionNotificationEmails` for the reason
        behind the queue itself.
        """
        self.pending_emails = []
        self.subscribers_want_notification = False

        diff_levels = (BranchSubscriptionNotificationLevel.DIFFSONLY,
                       BranchSubscriptionNotificationLevel.FULL)

        subscriptions = self.db_branch.getSubscriptionsByLevel(diff_levels)
        for subscription in subscriptions:
            self.subscribers_want_notification = True

        # If db_history is empty, then this is the initial scan of the
        # branch.  We only want to send one email for the initial scan
        # of a branch, not one for each revision.
        self.initial_scan = initial_scan

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
                self.db_branch, revno='removed', from_address=self.email_from,
                body=contents, perform_diff=False, subject=None)
            self.pending_emails.append(job)

    def sendRevisionNotificationEmails(self, bzr_history):
        """Send out the pending emails.

        If this is the first scan of a branch, then we send out a simple
        notification email saying that the branch has been scanned.
        """
        # XXX: thumper 2007-03-28 bug=29744:
        # The whole reason that this method exists is due to
        # emails being sent immediately in a zopeless environment.
        # When bug #29744 is fixed, this method will no longer be
        # necessary, and the emails should be sent at the source
        # instead of appending them to the pending_emails.
        # This method is enclosed in a transaction so emails will
        # continue to be sent out when the bug is closed without
        # immediately having to fix this method.
        # Now that these changes have been committed, send the pending emails.
        if not self.subscribers_want_notification:
            return
        self.trans_manager.begin()

        if self.initial_scan:
            assert len(self.pending_emails) == 0, (
                'Unexpected pending emails on new branch.')
            revision_count = len(bzr_history)
            if revision_count == 1:
                revisions = '1 revision'
            else:
                revisions = '%d revisions' % revision_count
            message = ('First scan of the branch detected %s'
                       ' in the revision history of the branch.' %
                       revisions)

            job = getUtility(IRevisionMailJobSource).create(
                self.db_branch, 'initial', self.email_from, message, False,
                None)
        self.trans_manager.commit()

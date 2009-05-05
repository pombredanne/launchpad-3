# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Email code for the branch scanner."""

__metaclass__ = type
__all__ = [
    'send_removed_revision_emails',
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


@adapter(events.RevisionsRemoved)
def send_removed_revision_emails(revisions_removed):
    """Notify subscribers of removed revisions.

    When the history is shortened, we send an email that says this.
    """
    if not subscribers_want_notification(revisions_removed.db_branch):
        return
    number_removed = len(revisions_removed.removed_history)
    if number_removed == 0:
        return
    if number_removed == 1:
        contents = '1 revision was removed from the branch.'
    else:
        contents = ('%d revisions were removed from the branch.'
                    % number_removed)
    # No diff is associated with the removed email.
    getUtility(IRevisionMailJobSource).create(
        revisions_removed.db_branch, revno='removed',
        from_address=config.canonical.noreply_from_address,
        body=contents, perform_diff=False, subject=None)


@adapter(events.TipChanged)
def send_tip_changed_emails(tip_changed):
    if not subscribers_want_notification(tip_changed.db_branch):
        return
    if tip_changed.initial_scan:
        revision_count = tip_changed.bzr_branch.revno()
        if revision_count == 1:
            revisions = '1 revision'
        else:
            revisions = '%d revisions' % revision_count
        message = ('First scan of the branch detected %s'
                   ' in the revision history of the branch.' %
                   revisions)
        getUtility(IRevisionMailJobSource).create(
            tip_changed.db_branch, 'initial',
            config.canonical.noreply_from_address, message, False, None)
    else:
        getUtility(IRevisionsAddedJobSource).create(
            tip_changed.db_branch, tip_changed.db_branch.last_scanned_id,
            tip_changed.bzr_branch.last_revision(),
            config.canonical.noreply_from_address)

# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Email notifications related to branch merge proposals."""


__metaclass__ = type


from canonical.launchpad.interfaces import CodeReviewNotificationLevel


def send_merge_proposal_created_notifications(merge_proposal, event):
    """Notify branch subscribers when merge proposals are created."""
    recipients = merge_proposal.getCreationNotificationRecipients(
        CodeReviewNotificationLevel.FULL)

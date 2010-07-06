# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""BugNotificationMailer code, based on `BaseMailer`."""

__metaclass__ = type
__all__ = [
    'BugNotificationMailer',
    ]

from canonical.config import config

from lp.bugs.mail.bugnotificationbuilder import (
    get_bugmail_from_address, get_bugmail_replyto_address)
from lp.services.mail.basemailer import BaseMailer


class BugNotificationMailer(BaseMailer):
    """A `BaseMailer` subclass for sending `BugNotification`s."""

    def __init__(self, bug_notification, template_name, message_id=None,
                 notification_type=None):
        from_address = get_bugmail_from_address(
            bug_notification.message.owner,
            bug_notification.bug)

        super(BugNotificationMailer, self).__init__(
            bug_notification.message.subject, template_name,
            recipients={}, from_address=from_address, delta=None,
            message_id=message_id, notification_type=notification_type)

        self.bug_notification = bug_notification
        self.bug = bug_notification.bug

        # We clobber the super()'d version of _recipients and replace it
        # with that which comes from the notififcation.
        self._recipients = self.bug.getBugNotificationRecipients()

    def _getHeaders(self, email):
        """See `BaseMailer`."""
        reason_text, reason_header = self._recipients.getReason(email)
        headers = {'X-Launchpad-Message-Rationale': reason_header}

        headers['Reply-To'] = get_bugmail_replyto_address(self.bug)
        headers['Sender'] = config.canonical.bounce_address

        # X-Launchpad-Bug
        headers['X-Launchpad-Bug'] = [
            bugtask.asEmailHeaderValue() for bugtask in self.bug.bugtasks]

        # X-Launchpad-Bug-Tags
        if len(self.bug.tags) > 0:
            headers['X-Launchpad-Bug-Tags'] = ' '.join(self.bug.tags)

        # Add the X-Launchpad-Bug-Private header. This is a simple
        # yes/no value denoting privacy for the bug.
        if self.bug.private:
            headers['X-Launchpad-Bug-Private'] = 'yes'
        else:
            headers['X-Launchpad-Bug-Private'] = 'no'

        # Add the X-Launchpad-Bug-Security-Vulnerability header to
        # denote security for this bug. This follows the same form as
        # the -Bug-Private header.
        if self.bug.security_related:
            headers['X-Launchpad-Bug-Security-Vulnerability'] = 'yes'
        else:
            headers['X-Launchpad-Bug-Security-Vulnerability'] = 'no'

        # Add the -Bug-Commenters header, a space-separated list of
        # distinct IDs of people who have commented on the bug. The
        # list is sorted to aid testing.
        commenters = set(message.owner.name for message in self.bug.messages)
        headers['X-Launchpad-Bug-Commenters'] = ' '.join(sorted(commenters))

        # Add the -Bug-Reporter header to identify the owner of the bug
        # and the original bug task for filtering
        headers['X-Launchpad-Bug-Reporter'] = (
            '%s (%s)' % (self.bug.owner.displayname, self.bug.owner.name))

        return headers

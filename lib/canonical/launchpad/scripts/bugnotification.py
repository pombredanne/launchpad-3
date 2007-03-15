# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functions related to sending bug notifications."""

__metaclass__ = type

from email.MIMEText import MIMEText
from email.Utils import formatdate
import rfc822

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import rollback, begin
from canonical.launchpad.helpers import (
    get_email_template, shortlist, contactEmailAddresses)
from canonical.launchpad.interfaces import IEmailAddressSet
from canonical.launchpad.mail import format_address
from canonical.launchpad.mailnotification import (
    get_bugmail_replyto_address, generate_bug_add_email, MailWrapper,
    GLOBAL_NOTIFICATION_EMAIL_ADDRS)
from canonical.launchpad.scripts.logger import log
from canonical.launchpad.webapp import canonical_url
from canonical.lp.dbschema import EmailAddressStatus


class BugNotificationRationale:
    """XXX"""
    def __init__(self, duplicateof=None):
        self._reasons = {}
        self.duplicateof = duplicateof

    def _addReason(self, person, reason, header):
        if self.duplicateof is not None:
            # XXX: this is not the same as subscriber of duplicate!
            reason = reason + " (via bug %s)" % self.duplicateof
            header = header + "via Bug %s" % self.duplicateof
        reason = "You received this bug notification because you %s." % reason
        for email in contactEmailAddresses(person):
            if email not in self._reasons:
                # XXX: avoid clobbering; FCFS
                self._reasons[email] = (reason, header)

    def update(self, rationale):
        for k, v in rationale._reasons:
            if k not in self._reasons:
                self._reasons[k] = v

    def getReason(self, email):
        return self._reasons[email]

    def getAddresses(self):
        return sorted(self._reasons.keys())

    def addExtraEmail(self, email):
        self._reasons[email] = ("XXX", "XXX")

    def addDupeSubscriber(self, person):
        if person.isTeam():
            text = ("are a member of %s, which is a subscriber "
                    "of a duplicate bug" % person.displayname)
        else:
            text = "are a direct subscriber of a duplicate bug"
        self._addReason(person, text, "Direct Subscriber of Duplicate")

    def addDirectSubscriber(self, person):
        if person.isTeam():
            text = "are a member of %s, which is a direct subscriber" % person.displayname
        else:
            text = "are a direct subscriber of the bug"
        self._addReason(person, text, "Direct Subscriber")

    def addAssignee(self, person):
        if person.isTeam():
            text = "are a member of %s, which is a bug assignee" % person.displayname
        else:
            text = "are a bug assignee"
        self._addReason(person, text, "Assignee")

    def addDistroBugContact(self, person, distro):
        if person.isTeam():
            text = ("are a member of %s, which is the bug contact for %s" %
                (person.displayname, distro.displayname))
        else:
            text = "are the bug contact for %s" % distro.displayname
        self._addReason(person, text, "%s Bug Contact" % distro.displayname)

    def addPackageBugContact(self, person, package):
        if person.isTeam():
            text = ("are a member of %s, which is a bug contact for %s" %
                (person.displayname, package.displayname))
        else:
            text = "are a bug contact for %s" % package.displayname
        self._addReason(person, text, "%s Bug Contact" % package.displayname)

    def addUpstreamBugContact(self, person, upstream):
        if person.isTeam():
            text = ("are a member of %s, which is the bug contact for %s" %
                (person.displayname, upstream.displayname))
        else:
            text = "are the bug contact for %s" % upstream.displayname
        self._addReason(person, text, "%s Bug Contact" % upstream.displayname)

    def addUpstreamRegistrant(self, person, upstream):
        if person.isTeam():
            text = ("are a member of %s, which is the registrant for %s" %
                (person.displayname, upstream.displayname))
        else:
            text = "are the registrant for %s" % upstream.displayname
        self._addReason(person, text, "%s Registrant" % upstream.displayname)


def construct_email_notification(bug_notifications):
    """Construct an email from a list of related bug notifications.

    The person and bug has to be the same for all notifications, and
    there can be only one comment.
    """
    first_notification = bug_notifications[0]
    bug = first_notification.bug
    person = first_notification.message.owner
    subject = first_notification.message.subject

    comment = None
    references = []
    text_notifications = []
    rationale = BugNotificationRationale()

    bug.registerBugSubscribers(rationale)
    if not bug.private and GLOBAL_NOTIFICATION_EMAIL_ADDRS:
        for address in GLOBAL_NOTIFICATION_EMAIL_ADDRS:
            rationale.addExtraEmail(address)

    for notification in bug_notifications:
        assert notification.bug == bug
        assert notification.message.owner == person
        if notification.is_comment:
            assert comment is None, (
                "Only one of the notifications is allowed to be a comment.")
            comment = notification.message

    if bug.duplicateof is not None:
        text_notifications.append(
            '*** This bug is a duplicate of bug %d ***\n\t%s' %
                (bug.duplicateof.id, canonical_url(bug.duplicateof)))

        if not bug.private:
            # This bug is a public duplicate of another bug, so include
            # the dupe target's subscribers in the recipient list. Note
            # that we only do this for duplicate bugs that are public;
            # changes in private bugs are not broadcast to their dupe
            # targets.
            dupe_rationale = BugNotificationRationale(duplicateof=bug.duplicateof)
            bug.duplicateof.registerSubscribersAndRationales(dupe_rationale)
            rationale = rationale.update(dupe_rationale)

    if comment is not None:
        if comment == bug.initial_message:
            dummy, text = generate_bug_add_email(bug)
        else:
            text = comment.text_contents
        text_notifications.append(text)

        msgid = comment.rfc822msgid
        email_date = comment.datecreated

        reference = comment.parent
        while reference is not None:
            references.insert(0, reference.rfc822msgid)
            reference = reference.parent
    else:
        msgid = first_notification.message.rfc822msgid
        email_date = first_notification.message.datecreated

    if bug.initial_message.rfc822msgid not in references:
        references.insert(0, bug.initial_message.rfc822msgid)

    for notification in bug_notifications:
        if notification.message != comment:
            text = notification.message.text_contents.rstrip()
            text_notifications.append(text)

    mail_wrapper = MailWrapper(width=72)
    content = '\n\n'.join(text_notifications)

    if person.preferredemail is not None:
        from_address = format_address(
            person.displayname, person.preferredemail.email)
    else:
        # XXX: The person doesn't have a preferred email set, but he
        #      added a comment via the email UI. It shouldn't be
        #      possible to use the email UI if you don't have a
        #      preferred email set, but work around it for now by
        #      setting the from address as the first validated address,
        #      or if that fails, simply anyone if his address.
        #      -- Bjorn Tillenius, 2006-04-05
        for email in getUtility(IEmailAddressSet).getByPerson(person):
            if email.status == EmailAddressStatus.VALIDATED:
                from_email = email.email
                break
        else:
            # Since he added a comment, he's bound to have at least one
            # address.
            email_addresses = shortlist(
                getUtility(IEmailAddressSet).getByPerson(person))
            if len(email_addresses) > 0:
                # We have no idea of which email address is best to use,
                # just choose the first one.
                email = email_addresses[0]
                from_email = email.email
            else:
                # XXX: A user should always have at least one email
                # address, but due to bug 33427, this isn't always the
                # case. -- Bjorn Tillenius, 2006-05-21
                log.error(
                    "The user %r has no email addresses. This happened"
                    " while sending notifications for bug %s." % (
                        person.name, bug.id))
                from_email = "%s@%s" % (bug.id, config.launchpad.bugs_domain)

        from_address = format_address(person.displayname, from_email)

    messages = []
    for address in rationale.getAddresses():
        reason, rationale_header = rationale.getReason(address)
        body = get_email_template('bug-notification.txt') % {
            'content': mail_wrapper.format(content),
            'bug_title': bug.title,
            'bug_url': canonical_url(bug),
            'notification_rationale': mail_wrapper.format(reason)}
        msg = MIMEText(body.encode('utf8'), 'plain', 'utf8')
        msg['From'] = from_address
        msg['To'] = address
        msg['Reply-To'] = get_bugmail_replyto_address(bug)
        msg['References'] = ' '.join(references)
        msg['Sender'] = config.bounce_address
        msg['Date'] = formatdate(rfc822.mktime_tz(email_date.utctimetuple() + (0,)))
        msg['Message-Id'] = msgid
        subject_prefix = "[Bug %d]" % bug.id
        if subject_prefix in subject:
            msg['Subject'] = subject
        else:
            msg['Subject'] = "%s %s" % (subject_prefix, subject)

        # Add X-Launchpad-Bug headers.
        for bugtask in bug.bugtasks:
            msg.add_header('X-Launchpad-Bug', bugtask.asEmailHeaderValue())

        msg.add_header('X-Launchpad-Bug-Rationale', rationale_header)
        messages.append(msg)

    return bug_notifications, messages

def _log_exception_and_restart_transaction():
    """Log an execption and restart the current transaction.

    It's important to restart the transaction if an exception occurs,
    since if it's a DB exception, the transaction isn't usable anymore.
    """
    log.exception(
        "An exception was raised while building the email notification.")
    rollback()
    begin()


def get_email_notifications(bug_notifications, date_emailed=None):
    """Return the email notifications pending to be sent."""
    bug_notifications = list(bug_notifications)
    while bug_notifications:
        person_bug_notifications = []
        bug = bug_notifications[0].bug
        person = bug_notifications[0].message.owner
        # Create a copy of the list, so removing items from it won't
        # break the iteration over it.
        for notification in list(bug_notifications):
            if (notification.bug, notification.message.owner) != (bug, person):
                break
            person_bug_notifications.append(notification)
            bug_notifications.remove(notification)

        has_comment = False
        notifications_to_send = []
        for notification in person_bug_notifications:
            if date_emailed is not None:
                notification.date_emailed = date_emailed
            if notification.is_comment and has_comment:
                try:
                    yield construct_email_notification(notifications_to_send)
                except:
                    # We don't want bugs preventing all bug
                    # notifications from being sent, so catch all
                    # exceptions and log them.
                    _log_exception_and_restart_transaction()
                has_comment = False
                notifications_to_send = []
            if notification.is_comment:
                has_comment = True
            notifications_to_send.append(notification)
        if notifications_to_send:
            try:
                yield construct_email_notification(notifications_to_send)
            except:
                # We don't want bugs preventing all bug
                # notifications from being sent, so catch all
                # exceptions and log them.
                _log_exception_and_restart_transaction()

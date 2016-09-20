# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug notification building code."""

__metaclass__ = type
__all__ = [
    'BugNotificationBuilder',
    'format_rfc2822_date',
    'get_bugmail_error_address',
    'get_bugmail_from_address',
    ]

from email.mime.text import MIMEText
from email.utils import formatdate
import re
import rfc822

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import (
    PRIVATE_INFORMATION_TYPES,
    SECURITY_INFORMATION_TYPES,
    )
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.services.config import config
from lp.services.helpers import shortlist
from lp.services.identity.interfaces.emailaddress import IEmailAddressSet
from lp.services.mail.sendmail import (
    append_footer,
    format_address,
    )


def format_rfc2822_date(date):
    """Formats a date according to RFC2822's desires."""
    return formatdate(rfc822.mktime_tz(date.utctimetuple() + (0, )))


def get_bugmail_from_address(person, bug):
    """Returns the right From: address to use for a bug notification."""
    if person == getUtility(ILaunchpadCelebrities).janitor:
        return format_address(
            'Launchpad Bug Tracker',
            "%s@%s" % (bug.id, config.launchpad.bugs_domain))

    if person.hide_email_addresses:
        return format_address(
            person.displayname,
            "%s@%s" % (bug.id, config.launchpad.bugs_domain))

    if person.preferredemail is not None:
        return format_address(person.displayname, person.preferredemail.email)

    # XXX: Bjorn Tillenius 2006-04-05:
    # The person doesn't have a preferred email set, but they
    # added a comment (either via the email UI, or because they were
    # imported as a deaf reporter). It shouldn't be possible to use the
    # email UI if you don't have a preferred email set, but work around
    # it for now by trying hard to find the right email address to use.
    email_addresses = shortlist(
        getUtility(IEmailAddressSet).getByPerson(person))
    if not email_addresses:
        # XXX: Bjorn Tillenius 2006-05-21 bug=33427:
        # A user should always have at least one email address,
        # but due to bug #33427, this isn't always the case.
        return format_address(person.displayname,
            "%s@%s" % (bug.id, config.launchpad.bugs_domain))

    # At this point we have no validated emails to use: if any of the
    # person's emails had been validated the preferredemail would be
    # set. Since we have no idea of which email address is best to use,
    # we choose the first one.
    return format_address(person.displayname, email_addresses[0].email)


def get_bugmail_replyto_address(bug):
    """Return an appropriate bugmail Reply-To address.

    :bug: the IBug.

    :user: an IPerson whose name will appear in the From address, e.g.:

        From: Foo Bar via Malone <123@bugs...>
    """
    return u"Bug %d <%s@%s>" % (bug.id, bug.id, config.launchpad.bugs_domain)


def get_bugmail_error_address():
    """Return a suitable From address for a bug transaction error email."""
    return config.malone.bugmail_error_from_address


class BugNotificationBuilder:
    """Constructs a MIMEText message for a bug notification.

    Takes a bug and a set of headers and returns a new MIMEText
    object. Common and expensive to calculate headers are cached
    up-front.
    """

    def __init__(self, bug, event_creator=None):
        self.bug = bug

        # Pre-calculate common headers.
        self.common_headers = [
            ('Reply-To', get_bugmail_replyto_address(bug)),
            ('Sender', config.canonical.bounce_address),
            ('X-Launchpad-Notification-Type', 'bug'),
            ]

        # X-Launchpad-Bug
        self.common_headers.extend(
            ('X-Launchpad-Bug', bugtask.asEmailHeaderValue())
            for bugtask in bug.bugtasks)

        # X-Launchpad-Bug-Tags
        if len(bug.tags) > 0:
            self.common_headers.append(
                ('X-Launchpad-Bug-Tags', ' '.join(bug.tags)))

        self.common_headers.append(
            ('X-Launchpad-Bug-Information-Type',
             bug.information_type.title))

        # For backwards compatibility, we still include the
        # X-Launchpad-Bug-Private and X-Launchpad-Bug-Security-Vulnerability
        # headers.
        if bug.information_type in PRIVATE_INFORMATION_TYPES:
            self.common_headers.append(
                ('X-Launchpad-Bug-Private', 'yes'))
        else:
            self.common_headers.append(
                ('X-Launchpad-Bug-Private', 'no'))

        if bug.information_type in SECURITY_INFORMATION_TYPES:
            self.common_headers.append(
                ('X-Launchpad-Bug-Security-Vulnerability', 'yes'))
        else:
            self.common_headers.append(
                ('X-Launchpad-Bug-Security-Vulnerability', 'no'))

        # Add the -Bug-Commenters header, a space-separated list of
        # distinct IDs of people who have commented on the bug. The
        # list is sorted to aid testing.
        commenters = set(message.owner.name for message in bug.messages)
        self.common_headers.append(
            ('X-Launchpad-Bug-Commenters', ' '.join(sorted(commenters))))

        # Add the -Bug-Reporter header to identify the owner of the bug
        # and the original bug task for filtering.
        self.common_headers.append(
            ('X-Launchpad-Bug-Reporter',
             '%s (%s)' % (bug.owner.displayname, bug.owner.name)))

        # Add the -Bug-Modifier header to identify the person who
        # modified the bug report.
        if event_creator:
            self.common_headers.append(
                ('X-Launchpad-Bug-Modifier',
                    '%s (%s)' % (event_creator.displayname,
                        event_creator.name)))

        if bug.duplicateof is not None:
            self.common_headers.append(
                ('X-Launchpad-Bug-Duplicate', str(bug.duplicateof.id)))

    def build(self, from_address, to_person, body, subject, email_date,
              rationale=None, references=None, message_id=None, filters=None):
        """Construct the notification.

        :param from_address: The From address of the notification.
        :param to_person: The `IPerson` to use as the To address for the
            notification.
        :param body: The body text of the notification.
        :type body: unicode
        :param subject: The Subject of the notification.
        :param email_date: The Date for the notification.
        :param rationale: The rationale for why the recipient is
            receiving this notification.
        :param references: A value for the References header.
        :param message_id: A value for the Message-ID header.

        :return: An `email.mime.text.MIMEText` object.
        """
        headers = [
            ('Date', format_rfc2822_date(email_date)),
            ('From', from_address),
            ('To', str(removeSecurityProxy(to_person).preferredemail.email)),
            ]

        # Add the common headers.
        headers.extend(self.common_headers)

        if references:
            headers.append(('References', ' '.join(references)))
        if message_id is not None:
            headers.append(('Message-Id', message_id))

        subject_prefix = "[Bug %d]" % self.bug.id
        if subject is None:
            headers.append(('Subject', subject_prefix))
        elif subject_prefix in subject:
            headers.append(('Subject', subject))
        else:
            headers.append(('Subject', "%s %s" % (subject_prefix, subject)))

        if rationale is not None:
            headers.append(('X-Launchpad-Message-Rationale', rationale))
            # XXX cjwatson 2015-09-11: The ridiculously complicated way that
            # bug notifications are built means that we no longer have
            # direct access to the subscriber name at this point.  As a
            # stopgap, parse it out of the rationale.
            match = re.search(r'@([^ ]*)', rationale)
            if match is not None:
                message_for = match.group(1)
            else:
                message_for = removeSecurityProxy(to_person).name
            headers.append(('X-Launchpad-Message-For', message_for))

        if filters is not None:
            for filter in filters:
                headers.append(('X-Launchpad-Subscription', filter))

        # XXX cjwatson 2015-07-31: This is cloned-and-hacked from
        # BaseMailer; it would ultimately be better to convert bug
        # notifications to that framework.
        if removeSecurityProxy(to_person).expanded_notification_footers:
            lines = []
            for key, value in headers:
                if key.startswith('X-Launchpad-'):
                    lines.append('%s: %s\n' % (key[2:], value))
            if lines:
                body = append_footer(body, ''.join(lines))

        message = MIMEText(body.encode('utf8'), 'plain', 'utf8')
        for header in headers:
            message.add_header(*header)
        return message

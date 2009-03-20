# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

# XXX: Gavin Panella 2008-11-21 bug=300725: This module need
# refactoring and/or splitting into a package or packages.

"""Event handlers that send email notifications."""

__metaclass__ = type

import datetime
from difflib import unified_diff
import operator

from email.Header import Header
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEMessage import MIMEMessage
from email.Utils import formataddr, formatdate, make_msgid

import re
import rfc822

from zope.component import getAdapter, getUtility
from zope.interface import implements
from zope.security.proxy import isinstance as zope_isinstance

from canonical.config import config
from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.components.bugchange import get_bug_change_class
from canonical.launchpad.interfaces import (
    IEmailAddressSet, IHeldMessageDetails, ILaunchpadCelebrities,
    INotificationRecipientSet, IPerson, IPersonSet, ISpecification,
    IStructuralSubscriptionTarget, ITeamMembershipSet, IUpstreamBugTask,
    TeamMembershipStatus)
from canonical.launchpad.interfaces.bugchange import IBugChange
from canonical.launchpad.interfaces.message import (
    IDirectEmailAuthorization, QuotaReachedError)
from canonical.launchpad.interfaces.structuralsubscription import (
    BugNotificationLevel)
from canonical.launchpad.mail import (
    sendmail, simple_sendmail, simple_sendmail_from_person, format_address)
from canonical.launchpad.mailout.mailwrapper import MailWrapper
from canonical.launchpad.mailout.notificationrecipientset import (
    NotificationRecipientSet)
from canonical.launchpad.components.bug import BugDelta
from canonical.launchpad.helpers import (
    get_contact_email_addresses, get_email_template, shortlist)
from canonical.launchpad.webapp import canonical_url


CC = "CC"


class BugNotificationRecipients(NotificationRecipientSet):
    """A set of emails and rationales notified for a bug change.

    Each email address registered in a BugNotificationRecipients is
    associated to a string and a header that explain why the address is
    being emailed. For instance, if the email address is that of a
    distribution bug supervisor for a bug, the string and header will make
    that fact clear.

    The string is meant to be rendered in the email footer. The header
    is meant to be used in an X-Launchpad-Message-Rationale header.

    The first rationale registered for an email address is the one
    which will be used, regardless of other rationales being added
    for it later. This gives us a predictable policy of preserving
    the first reason added to the registry; the callsite should
    ensure that the manipulation of the BugNotificationRecipients
    instance is done in preferential order.

    Instances of this class are meant to be returned by
    IBug.getBugNotificationRecipients().
    """
    implements(INotificationRecipientSet)
    def __init__(self, duplicateof=None):
        """Constructs a new BugNotificationRecipients instance.

        If this bug is a duplicate, duplicateof should be used to
        specify which bug ID it is a duplicate of.

        Note that there are two duplicate situations that are
        important:
          - One is when this bug is a duplicate of another bug:
            the subscribers to the main bug get notified of our
            changes.
          - Another is when the bug we are changing has
            duplicates; in that case, direct subscribers of
            duplicate bugs get notified of our changes.
        These two situations are catered respectively by the
        duplicateof parameter above and the addDupeSubscriber method.
        Don't confuse them!
        """
        NotificationRecipientSet.__init__(self)
        self.duplicateof = duplicateof

    def _addReason(self, person, reason, header):
        """Adds a reason (text and header) for a person.

        It takes care of modifying the message when the person is notified
        via a duplicate.
        """
        if self.duplicateof is not None:
            reason = reason + " (via bug %s)" % self.duplicateof.id
            header = header + " via Bug %s" % self.duplicateof.id
        reason = "You received this bug notification because you %s." % reason
        self.add(person, reason, header)

    def addDupeSubscriber(self, person):
        """Registers a subscriber of a duplicate of this bug."""
        reason = "Subscriber of Duplicate"
        if person.isTeam():
            text = ("are a member of %s, which is a subscriber "
                    "of a duplicate bug" % person.displayname)
            reason += " @%s" % person.name
        else:
            text = "are a direct subscriber of a duplicate bug"
        self._addReason(person, text, reason)

    def addDirectSubscriber(self, person):
        """Registers a direct subscriber of this bug."""
        reason = "Subscriber"
        if person.isTeam():
            text = ("are a member of %s, which is a direct subscriber"
                    % person.displayname)
            reason += " @%s" % person.name
        else:
            text = "are a direct subscriber of the bug"
        self._addReason(person, text, reason)

    def addAssignee(self, person):
        """Registers an assignee of a bugtask of this bug."""
        reason = "Assignee"
        if person.isTeam():
            text = ("are a member of %s, which is a bug assignee"
                    % person.displayname)
            reason += " @%s" % person.name
        else:
            text = "are a bug assignee"
        self._addReason(person, text, reason)

    def addDistroBugSupervisor(self, person, distro):
        """Registers a distribution bug supervisor for this bug."""
        reason = "Bug Supervisor (%s)" % distro.displayname
        # All displaynames in these reasons should be changed to bugtargetname
        # (as part of bug 113262) once bugtargetname is finalized for packages
        # (bug 113258). Changing it before then would be excessively
        # disruptive.
        if person.isTeam():
            text = ("are a member of %s, which is the bug supervisor for %s" %
                (person.displayname, distro.displayname))
            reason += " @%s" % person.name
        else:
            text = "are the bug supervisor for %s" % distro.displayname
        self._addReason(person, text, reason)

    def addStructuralSubscriber(self, person, target):
        """Registers a structural subscriber to this bug's target."""
        reason = "Subscriber (%s)" % target.displayname
        if person.isTeam():
            text = ("are a member of %s, which is subscribed to %s" %
                (person.displayname, target.displayname))
            reason += " @%s" % person.name
        else:
            text = "are subscribed to %s" % target.displayname
        self._addReason(person, text, reason)

    def addUpstreamBugSupervisor(self, person, upstream):
        """Registers an upstream bug supervisor for this bug."""
        reason = "Bug Supervisor (%s)" % upstream.displayname
        if person.isTeam():
            text = ("are a member of %s, which is the bug supervisor for %s" %
                (person.displayname, upstream.displayname))
            reason += " @%s" % person.name
        else:
            text = "are the bug supervisor for %s" % upstream.displayname
        self._addReason(person, text, reason)

    def addRegistrant(self, person, upstream):
        """Registers an upstream product registrant for this bug."""
        reason = "Registrant (%s)" % upstream.displayname
        if person.isTeam():
            text = ("are a member of %s, which is the registrant for %s" %
                (person.displayname, upstream.displayname))
            reason += " @%s" % person.name
        else:
            text = "are the registrant for %s" % upstream.displayname
        self._addReason(person, text, reason)


def format_rfc2822_date(date):
    """Formats a date according to RFC2822's desires."""
    return formatdate(rfc822.mktime_tz(date.utctimetuple() + (0,)))


class BugNotificationBuilder:
    """Constructs a MIMEText message for a bug notification.

    Takes a bug and a set of headers and returns a new MIMEText
    object. Common and expensive to calculate headers are cached
    up-front.
    """

    def __init__(self, bug):
        self.bug = bug

        # Pre-calculate common headers.
        self.common_headers = [
            ('Reply-To', get_bugmail_replyto_address(bug)),
            ('Sender', config.canonical.bounce_address),
            ]

        # X-Launchpad-Bug
        self.common_headers.extend(
            ('X-Launchpad-Bug', bugtask.asEmailHeaderValue())
            for bugtask in bug.bugtasks)

        # X-Launchpad-Bug-Tags
        if len(bug.tags) > 0:
            self.common_headers.append(
                ('X-Launchpad-Bug-Tags', ' '.join(bug.tags)))

        # Add the X-Launchpad-Bug-Private header. This is a simple
        # yes/no value denoting privacy for the bug.
        if bug.private:
            self.common_headers.append(
                ('X-Launchpad-Bug-Private', 'yes'))
        else:
            self.common_headers.append(
                ('X-Launchpad-Bug-Private', 'no'))

        # Add the X-Launchpad-Bug-Security-Vulnerability header to
        # denote security for this bug. This follows the same form as
        # the -Bug-Private header.
        if bug.security_related:
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

    def build(self, from_address, to_address, body, subject, email_date,
              rationale=None, references=None, message_id=None):
        """Construct the notification.

        :param from_address: The From address of the notification.
        :param to_address: The To address for the notification.
        :param body: The body text of the notification.
        :type body: unicode
        :param subject: The Subject of the notification.
        :param email_date: The Date for the notification.
        :param rationale: The rationale for why the recipient is
            receiving this notification.
        :param references: A value for the References header.
        :param message_id: A value for the Message-ID header.

        :return: An `email.MIMEText.MIMEText` object.
        """
        message = MIMEText(body.encode('utf8'), 'plain', 'utf8')
        message['Date'] = format_rfc2822_date(email_date)
        message['From'] = from_address
        message['To'] = to_address

        # Add the common headers.
        for header in self.common_headers:
            message.add_header(*header)

        if references is not None:
            message['References'] = ' '.join(references)
        if message_id is not None:
            message['Message-Id'] = message_id

        subject_prefix = "[Bug %d]" % self.bug.id
        if subject is None:
            message['Subject'] = subject_prefix
        elif subject_prefix in subject:
            message['Subject'] = subject
        else:
            message['Subject'] = "%s %s" % (subject_prefix, subject)

        if rationale is not None:
            message.add_header('X-Launchpad-Message-Rationale', rationale)

        return message


def _send_bug_details_to_new_bug_subscribers(
    bug, previous_subscribers, current_subscribers, subscribed_by=None):
    """Send an email containing full bug details to new bug subscribers.

    This function is designed to handle situations where bugtasks get
    reassigned to new products or sourcepackages, and the new bug subscribers
    need to be notified of the bug.
    """
    prev_subs_set = set(previous_subscribers)
    cur_subs_set = set(current_subscribers)
    new_subs = cur_subs_set.difference(prev_subs_set)

    to_addrs = set()
    for new_sub in new_subs:
        to_addrs.update(get_contact_email_addresses(new_sub))

    if not to_addrs:
        return

    from_addr = format_address(
        'Launchpad Bug Tracker',
        "%s@%s" % (bug.id, config.launchpad.bugs_domain))
    # Now's a good a time as any for this email; don't use the original
    # reported date for the bug as it will just confuse mailer and
    # recipient.
    email_date = datetime.datetime.now()

    # The new subscriber email is effectively the initial message regarding
    # a new bug. The bug's initial message is used in the References
    # header to establish the message's context in the email client.
    references = [bug.initial_message.rfc822msgid]
    recipients = bug.getBugNotificationRecipients()

    bug_notification_builder = BugNotificationBuilder(bug)
    for to_addr in sorted(to_addrs):
        reason, rationale = recipients.getReason(to_addr)
        subject, contents = generate_bug_add_email(
            bug, new_recipients=True, subscribed_by=subscribed_by,
            reason=reason)
        msg = bug_notification_builder.build(
            from_addr, to_addr, contents, subject, email_date,
            rationale=rationale, references=references)
        sendmail(msg)


@block_implicit_flushes
def update_security_contact_subscriptions(modified_bugtask, event):
    """Subscribe the new security contact when a bugtask's product changes.

    No change is made for private bugs.
    """
    if event.object.bug.private:
        return

    if not IUpstreamBugTask.providedBy(event.object):
        return

    bugtask_before_modification = event.object_before_modification
    bugtask_after_modification = event.object

    if (bugtask_before_modification.product !=
        bugtask_after_modification.product):
        new_product = bugtask_after_modification.product
        if new_product.security_contact:
            bugtask_after_modification.bug.subscribe(
                new_product.security_contact, IPerson(event.user))


def get_bugmail_from_address(person, bug):
    """Returns the right From: address to use for a bug notification."""
    if person == getUtility(ILaunchpadCelebrities).janitor:
        return format_address(
            'Launchpad Bug Tracker',
            "%s@%s" % (bug.id, config.launchpad.bugs_domain))

    if person.preferredemail is not None:
        return format_address(person.displayname, person.preferredemail.email)

    # XXX: Bjorn Tillenius 2006-04-05:
    # The person doesn't have a preferred email set, but he
    # added a comment (either via the email UI, or because he was
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


def send_process_error_notification(to_address, subject, error_msg,
                                    original_msg, failing_command=None):
    """Send a mail about an error occurring while using the email interface.

    Tells the user that an error was encountered while processing his
    request and attaches the original email which caused the error to
    happen.

        :to_address: The address to send the notification to.
        :subject: The subject of the notification.
        :error_msg: The error message that explains the error.
        :original_msg: The original message sent by the user.
        :failing_command: The command that caused the error to happen.
    """
    if isinstance(failing_command, list):
        failing_commands = failing_command
    elif failing_command is None:
        failing_commands = []
    else:
        failing_commands = [failing_command]
    failed_commands_information = ''
    if len(failing_commands) > 0:
        failed_commands_information = 'Failing command:'
        for failing_command in failing_commands:
            failed_commands_information += '\n    %s' % str(failing_command)

    body = get_email_template('email-processing-error.txt') % {
            'failed_command_information': failed_commands_information,
            'error_msg': error_msg}
    mailwrapper = MailWrapper(width=72)
    body = mailwrapper.format(body)
    error_part = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')

    msg = MIMEMultipart()
    msg['To'] = to_address
    msg['From'] = get_bugmail_error_address()
    msg['Subject'] = subject
    msg.attach(error_part)
    msg.attach(MIMEMessage(original_msg))
    sendmail(msg)


def notify_errors_list(message, file_alias_url):
    """Sends an error to the Launchpad errors list."""
    template = get_email_template('notify-unhandled-email.txt')
    # We add the error message in as a header too
    # (X-Launchpad-Unhandled-Email) so we can create filters in the
    # Launchpad-Error-Reports Mailman mailing list.
    simple_sendmail(
        get_bugmail_error_address(), [config.launchpad.errors_address],
        'Unhandled Email: %s' % file_alias_url,
        template % {'url': file_alias_url, 'error_msg': message},
        headers={'X-Launchpad-Unhandled-Email': message}
        )


def generate_bug_add_email(bug, new_recipients=False, reason=None,
                           subscribed_by=None):
    """Generate a new bug notification from the given IBug.

    If new_recipients is supplied we generate a notification explaining
    that the new recipients have been subscribed to the bug. Otherwise
    it's just a notification of a new bug report.
    """
    subject = u"[Bug %d] [NEW] %s" % (bug.id, bug.title)
    contents = ''

    if bug.private:
        # This is a confidential bug.
        visibility = u"Private"
    else:
        # This is a public bug.
        visibility = u"Public"

    if bug.security_related:
        visibility += ' security'
        contents += '*** This bug is a security vulnerability ***\n\n'

    bug_info = []
    # Add information about the affected upstreams and packages.
    for bugtask in bug.bugtasks:
        bug_info.append(u"** Affects: %s" % bugtask.bugtargetname)
        bug_info.append(u"     Importance: %s" % bugtask.importance.title)

        if bugtask.assignee:
            # There's a person assigned to fix this task, so show that
            # information too.
            bug_info.append(
                u"     Assignee: %s" % bugtask.assignee.unique_displayname)
        bug_info.append(u"         Status: %s\n" % bugtask.status.title)

    if bug.tags:
        bug_info.append('\n** Tags: %s' % ' '.join(bug.tags))

    mailwrapper = MailWrapper(width=72)
    content_substitutions = {
        'visibility' : visibility,
        'bug_url' : canonical_url(bug),
        'bug_info': "\n".join(bug_info),
        'bug_title': bug.title,
        'description': mailwrapper.format(bug.description),
        'notification_rationale': reason
        }

    if new_recipients:
        contents += "You have been subscribed to a %(visibility)s bug"
        if subscribed_by is not None:
            contents += " by %(subscribed_by)s"
            content_substitutions['subscribed_by'] = (
                subscribed_by.unique_displayname)
        contents += (":\n\n"
                     "%(description)s\n\n%(bug_info)s")
        # The visibility appears mid-phrase so.. hack hack.
        content_substitutions['visibility'] = visibility.lower()
        # XXX: kiko, 2007-03-21:
        # We should really have a centralized way of adding this
        # footer, but right now we lack a INotificationRecipientSet
        # for this particular situation.
        contents += (
            "\n-- \n%(bug_title)s\n%(bug_url)s\n%(notification_rationale)s")
    else:
        contents += ("%(visibility)s bug reported:\n\n"
                     "%(description)s\n\n%(bug_info)s")

    contents = contents % content_substitutions

    contents = contents.rstrip()

    return (subject, contents)


def get_unified_diff(old_text, new_text, text_width):
    r"""Return a unified diff of the two texts.

    Before the diff is produced, the texts are wrapped to the given text
    width.

        >>> print get_unified_diff(
        ...     'Some text\nAnother line\n',
        ...     'Some more text\nAnother line\n',
        ...     text_width=72)
        - Some text
        + Some more text
          Another line

    """
    mailwrapper = MailWrapper(width=72)
    old_text_wrapped = mailwrapper.format(old_text or '')
    new_text_wrapped = mailwrapper.format(new_text or '')

    lines_of_context = len(old_text_wrapped.splitlines())
    text_diff = unified_diff(
        old_text_wrapped.splitlines(),
        new_text_wrapped.splitlines(),
        n=lines_of_context)
    # Remove the diff header, which consists of the first three
    # lines.
    text_diff = list(text_diff)[3:]
    # Let's simplify the diff output by removing the helper lines,
    # which begin with '?'.
    text_diff = [
        diff_line for diff_line in text_diff
        if not diff_line.startswith('?')
        ]
    # Add a whitespace between the +/- and the text line.
    text_diff = [
        re.sub('^([\+\- ])(.*)', r'\1 \2', line)
        for line in text_diff
        ]
    text_diff = '\n'.join(text_diff)
    return text_diff


def get_bug_edit_notification_texts(bug_delta):
    """Generate a list of edit notification texts based on the bug_delta.

    bug_delta is an object that provides IBugDelta. The return value
    is a list of unicode strings.
    """
    # figure out what's been changed; add that information to the
    # list as appropriate
    changes = []
    if bug_delta.duplicateof is not None:
        new_bug_dupe = bug_delta.duplicateof['new']
        old_bug_dupe = bug_delta.duplicateof['old']
        assert new_bug_dupe is not None or old_bug_dupe is not None
        assert new_bug_dupe != old_bug_dupe
        if old_bug_dupe is not None:
            change_info = (
                u"** This bug is no longer a duplicate of bug %d\n" %
                    old_bug_dupe.id)
            change_info += u'   %s' % old_bug_dupe.title
            changes.append(change_info)
        if new_bug_dupe is not None:
            change_info = (
                u"** This bug has been marked a duplicate of bug %d\n" %
                    new_bug_dupe.id)
            change_info += '   %s' % new_bug_dupe.title
            changes.append(change_info)

    # The order of the field names in this list is important; this is
    # the order in which changes will appear both in the bug activity
    # log and in notification emails.
    bug_change_field_names = [
        'title', 'description', 'private', 'security_related', 'tags',
        'attachment',
        ]
    for field_name in bug_change_field_names:
        field_delta = getattr(bug_delta, field_name)
        if field_delta is not None:
            bug_change_class = get_bug_change_class(bug_delta.bug, field_name)
            change_info = bug_change_class(
                when=None, person=bug_delta.user, what_changed=field_name,
                old_value=field_delta['old'], new_value=field_delta['new'])
            changes.append(change_info)

    if bug_delta.bugtask_deltas is not None:
        bugtask_deltas = bug_delta.bugtask_deltas
        # Use zope_isinstance, to ensure that this Just Works with
        # security-proxied objects.
        if not zope_isinstance(bugtask_deltas, (list, tuple)):
            bugtask_deltas = [bugtask_deltas]
        for bugtask_delta in bugtask_deltas:
            change_info = u"** Changed in: %s\n" % (
                bugtask_delta.bugtask.bugtargetname)

            for fieldname, displayattrname in (
                ("product", "displayname"), ("sourcepackagename", "name"),
                ("importance", "title"), ("bugwatch", "title")):
                change = getattr(bugtask_delta, fieldname)
                if change:
                    oldval_display, newval_display = _get_task_change_values(
                        change, displayattrname)
                    change_info += _get_task_change_row(
                        fieldname, oldval_display, newval_display)

            if bugtask_delta.assignee is not None:
                oldval_display = u"(unassigned)"
                newval_display = u"(unassigned)"
                if bugtask_delta.assignee.get('old'):
                    oldval_display = (
                        bugtask_delta.assignee['old'].unique_displayname)
                if bugtask_delta.assignee.get('new'):
                    newval_display = (
                        bugtask_delta.assignee['new'].unique_displayname)

                changerow = (
                    u"%(label)13s: %(oldval)s => %(newval)s\n" % {
                    'label' : u"Assignee", 'oldval' : oldval_display,
                    'newval' : newval_display})
                change_info += changerow

            for fieldname, displayattrname in (
                ("status", "title"), ("target", "name")):
                change = getattr(bugtask_delta, fieldname)
                if change:
                    oldval_display, newval_display = _get_task_change_values(
                        change, displayattrname)
                    change_info += _get_task_change_row(
                        fieldname, oldval_display, newval_display)
            changes.append(change_info.rstrip())

    if bug_delta.added_bugtasks is not None:
        # Use zope_isinstance, to ensure that this Just Works with
        # security-proxied objects.
        if zope_isinstance(bug_delta.added_bugtasks, (list, tuple)):
            added_bugtasks = bug_delta.added_bugtasks
        else:
            added_bugtasks = [bug_delta.added_bugtasks]

        for added_bugtask in added_bugtasks:
            if added_bugtask.bugwatch:
                change_info = u"** Also affects: %s via\n" % (
                    added_bugtask.bugtargetname)
                change_info += u"   %s\n" % added_bugtask.bugwatch.url
            else:
                change_info = u"** Also affects: %s\n" % (
                    added_bugtask.bugtargetname)
            change_info += u"%13s: %s\n" % (u"Importance",
                added_bugtask.importance.title)
            if added_bugtask.assignee:
                assignee = added_bugtask.assignee
                change_info += u"%13s: %s\n" % (u"Assignee",
                    assignee.unique_displayname)
            change_info += u"%13s: %s" % (
                u"Status", added_bugtask.status.title)
            changes.append(change_info)

    return changes


def _get_task_change_row(label, oldval_display, newval_display):
    """Return a row formatted for display in task change info."""
    return u"%(label)13s: %(oldval)s => %(newval)s\n" % {
        'label' : label.capitalize(),
        'oldval' : oldval_display,
        'newval' : newval_display}


def _get_task_change_values(task_change, displayattrname):
    """Return the old value and the new value for a task field change."""
    oldval = task_change.get('old')
    newval = task_change.get('new')

    oldval_display = None
    newval_display = None

    if oldval:
        oldval_display = getattr(oldval, displayattrname)
    if newval:
        newval_display = getattr(newval, displayattrname)

    return (oldval_display, newval_display)


def get_bug_delta(old_bug, new_bug, user):
    """Compute the delta from old_bug to new_bug.

    old_bug and new_bug are IBug's. user is an IPerson. Returns an
    IBugDelta if there are changes, or None if there were no changes.
    """
    changes = {}

    for field_name in ("title", "description",  "name", "private",
                       "security_related", "duplicateof", "tags"):
        # fields for which we show old => new when their values change
        old_val = getattr(old_bug, field_name)
        new_val = getattr(new_bug, field_name)
        if old_val != new_val:
            changes[field_name] = {}
            changes[field_name]["old"] = old_val
            changes[field_name]["new"] = new_val

    if changes:
        changes["bug"] = new_bug
        changes["bug_before_modification"] = old_bug
        changes["bugurl"] = canonical_url(new_bug)
        changes["user"] = user

        return BugDelta(**changes)
    else:
        return None


@block_implicit_flushes
def notify_bug_added(bug, event):
    """Send an email notification that a bug was added.

    Event must be an IObjectCreatedEvent.
    """

    bug.addCommentNotification(bug.initial_message)


@block_implicit_flushes
def notify_bug_modified(modified_bug, event):
    """Notify the Cc'd list that this bug has been modified.

    modified_bug bug must be an IBug. event must be an
    IObjectModifiedEvent.
    """
    bug_delta = get_bug_delta(
        old_bug=event.object_before_modification,
        new_bug=event.object, user=IPerson(event.user))

    if bug_delta is not None:
        add_bug_change_notifications(bug_delta)


def get_bugtask_indirect_subscribers(bugtask, recipients=None, level=None):
    """Return the indirect subscribers for a bug task.

    Return the list of people who should get notifications about
    changes to the task because of having an indirect subscription
    relationship with it (by subscribing to its target, being an
    assignee or owner, etc...)

    If `recipients` is present, add the subscribers to the set of
    bug notification recipients.
    """
    if bugtask.bug.private:
        return set()

    also_notified_subscribers = set()

    # Assignees are indirect subscribers.
    if bugtask.assignee:
        also_notified_subscribers.add(bugtask.assignee)
        if recipients is not None:
            recipients.addAssignee(bugtask.assignee)

    if IStructuralSubscriptionTarget.providedBy(bugtask.target):
        also_notified_subscribers.update(
            bugtask.target.getBugNotificationsRecipients(
                recipients, level=level))

    if bugtask.milestone is not None:
        also_notified_subscribers.update(
            bugtask.milestone.getBugNotificationsRecipients(
                recipients, level=level))

    # If the target's bug supervisor isn't set,
    # we add the owner as a subscriber.
    pillar = bugtask.pillar
    if pillar.bug_supervisor is None:
        also_notified_subscribers.add(pillar.owner)
        if recipients is not None:
            recipients.addRegistrant(pillar.owner, pillar)

    return sorted(
        also_notified_subscribers,
        key=operator.attrgetter('displayname'))


def add_bug_change_notifications(bug_delta, old_bugtask=None):
    """Generate bug notifications and add them to the bug."""
    changes = get_bug_edit_notification_texts(bug_delta)
    recipients = bug_delta.bug.getBugNotificationRecipients(
        old_bug=bug_delta.bug_before_modification,
        level=BugNotificationLevel.METADATA)
    if old_bugtask is not None:
        old_bugtask_recipients = BugNotificationRecipients()
        get_bugtask_indirect_subscribers(
            old_bugtask, recipients=old_bugtask_recipients,
            level=BugNotificationLevel.METADATA)
        recipients.update(old_bugtask_recipients)
    for change in changes:
        # XXX 2009-03-17 gmb [bug=344125]
        #     This if..else should be removed once the new BugChange API
        #     is complete and ubiquitous.
        if IBugChange.providedBy(change):
            bug_delta.bug.addChange(change)
        else:
            bug_delta.bug.addChangeNotification(
                change, person=bug_delta.user, recipients=recipients)


@block_implicit_flushes
def notify_bugtask_added(bugtask, event):
    """Notify CC'd list that this bug has been marked as needing fixing
    somewhere else.

    bugtask must be in IBugTask. event must be an
    IObjectModifiedEvent.
    """
    bugtask = event.object

    bug_delta = BugDelta(
        bug=bugtask.bug,
        bugurl=canonical_url(bugtask.bug),
        user=IPerson(event.user),
        added_bugtasks=bugtask)

    add_bug_change_notifications(bug_delta)


@block_implicit_flushes
def notify_bugtask_edited(modified_bugtask, event):
    """Notify CC'd subscribers of this bug that something has changed
    on this task.

    modified_bugtask must be an IBugTask. event must be an
    IObjectModifiedEvent.
    """
    bugtask_delta = event.object.getDelta(event.object_before_modification)
    bug_delta = BugDelta(
        bug=event.object.bug,
        bugurl=canonical_url(event.object.bug),
        bugtask_deltas=bugtask_delta,
        user=IPerson(event.user))

    add_bug_change_notifications(
        bug_delta, old_bugtask=event.object_before_modification)

    previous_subscribers = event.object_before_modification.bug_subscribers
    current_subscribers = event.object.bug_subscribers
    _send_bug_details_to_new_bug_subscribers(
        event.object.bug, previous_subscribers, current_subscribers)
    update_security_contact_subscriptions(modified_bugtask, event)


@block_implicit_flushes
def notify_bug_comment_added(bugmessage, event):
    """Notify CC'd list that a message was added to this bug.

    bugmessage must be an IBugMessage. event must be an
    IObjectCreatedEvent. If bugmessage.bug is a duplicate the
    comment will also be sent to the dup target's subscribers.
    """
    bug = bugmessage.bug
    bug.addCommentNotification(bugmessage.message)


@block_implicit_flushes
def notify_bug_became_question(event):
    """Notify CC'd list that a bug was made into a question.

    The event must contain the bug that became a question, and the question
    that the bug became.
    """
    bug = event.bug
    question = event.question
    change_info = '\n'.join([
        '** bug changed to question:\n'
        '   %s' %  canonical_url(question)])
    bug.addChangeNotification(change_info, person=IPerson(event.user))


@block_implicit_flushes
def notify_bug_attachment_added(bugattachment, event):
    """Notify CC'd list that a new attachment has been added.

    bugattachment must be an IBugAttachment. event must be an
    IObjectCreatedEvent.
    """
    bug = bugattachment.bug
    bug_delta = BugDelta(
        bug=bug,
        bugurl=canonical_url(bug),
        user=IPerson(event.user),
        attachment={'new' : bugattachment, 'old': None})

    add_bug_change_notifications(bug_delta)


@block_implicit_flushes
def notify_bug_attachment_removed(bugattachment, event):
    """Notify that an attachment has been removed."""
    bug = bugattachment.bug
    bug_delta = BugDelta(
        bug=bug,
        bugurl=canonical_url(bug),
        user=IPerson(event.user),
        attachment={'old' : bugattachment, 'new': None})

    add_bug_change_notifications(bug_delta)


@block_implicit_flushes
def notify_bug_subscription_added(bug_subscription, event):
    """Notify that a new bug subscription was added."""
    # When a user is subscribed to a bug by someone other
    # than themselves, we send them a notification email.
    if bug_subscription.person != bug_subscription.subscribed_by:
        _send_bug_details_to_new_bug_subscribers(
            bug_subscription.bug, [], [bug_subscription.person],
            subscribed_by=bug_subscription.subscribed_by)


@block_implicit_flushes
def notify_invitation_to_join_team(event):
    """Notify team admins that the team has been invited to join another team.

    The notification will include a link to a page in which any team admin can
    accept the invitation.

    XXX: Guilherme Salgado 2007-05-08:
    At some point we may want to extend this functionality to allow invites
    to be sent to users as well, but for now we only use it for teams.
    """
    member = event.member
    assert member.isTeam()
    team = event.team
    membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
        member, team)
    assert membership is not None

    reviewer = membership.proposed_by
    admin_addrs = member.getTeamAdminsEmailAddresses()
    from_addr = format_address(
        team.displayname, config.canonical.noreply_from_address)
    subject = 'Invitation for %s to join' % member.name
    templatename = 'membership-invitation.txt'
    template = get_email_template(templatename)
    replacements = {
        'reviewer': '%s (%s)' % (reviewer.browsername, reviewer.name),
        'member': '%s (%s)' % (member.browsername, member.name),
        'team': '%s (%s)' % (team.browsername, team.name),
        'team_url': canonical_url(team),
        'membership_invitations_url':
            "%s/+invitation/%s" % (canonical_url(member), team.name)}
    for address in admin_addrs:
        recipient = getUtility(IPersonSet).getByEmail(address)
        replacements['recipient_name'] = recipient.displayname
        msg = MailWrapper().format(template % replacements, force_wrap=True)
        simple_sendmail(from_addr, address, subject, msg)


@block_implicit_flushes
def notify_team_join(event):
    """Notify team admins that someone has asked to join the team.

    If the team's policy is Moderated, the email will say that the membership
    is pending approval. Otherwise it'll say that the person has joined the
    team and who added that person to the team.
    """
    person = event.person
    team = event.team
    membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
        person, team)
    assert membership is not None
    approved, admin, proposed = [
        TeamMembershipStatus.APPROVED, TeamMembershipStatus.ADMIN,
        TeamMembershipStatus.PROPOSED]
    admin_addrs = team.getTeamAdminsEmailAddresses()
    from_addr = format_address(
        team.displayname, config.canonical.noreply_from_address)

    reviewer = membership.proposed_by
    if reviewer != person and membership.status in [approved, admin]:
        reviewer = membership.reviewed_by
        # Somebody added this person as a member, we better send a
        # notification to the person too.
        member_addrs = get_contact_email_addresses(person)

        subject = 'You have been added to %s' % team.name
        templatename = 'new-member-notification.txt'
        if person.isTeam():
            templatename = 'new-member-notification-for-teams.txt'
            subject = '%s joined %s' % (person.name, team.name)

        template = get_email_template(templatename)
        replacements = {
            'reviewer': '%s (%s)' % (reviewer.browsername, reviewer.name),
            'team_url': canonical_url(team),
            'member': '%s (%s)' % (person.browsername, person.name),
            'team': '%s (%s)' % (team.browsername, team.name)}
        for address in member_addrs:
            recipient = getUtility(IPersonSet).getByEmail(address)
            replacements['recipient_name'] = recipient.displayname
            msg = MailWrapper().format(
                template % replacements, force_wrap=True)
            simple_sendmail(from_addr, address, subject, msg)

        # The member's email address may be in admin_addrs too; let's remove
        # it so the member don't get two notifications.
        admin_addrs = set(admin_addrs).difference(set(member_addrs))

    # Yes, we can have teams with no members; not even admins.
    if not admin_addrs:
        return

    replacements = {
        'person_name': "%s (%s)" % (person.browsername, person.name),
        'team_name': "%s (%s)" % (team.browsername, team.name),
        'reviewer_name': "%s (%s)" % (reviewer.browsername, reviewer.name),
        'url': canonical_url(membership)}

    headers = {}
    if membership.status in [approved, admin]:
        template = get_email_template(
            'new-member-notification-for-admins.txt')
        subject = '%s joined %s' % (person.name, team.name)
    elif membership.status == proposed:
        if person.isTeam():
            headers = {"Reply-To": reviewer.preferredemail.email}
            template = get_email_template(
                'pending-membership-approval-for-teams.txt')
        else:
            headers = {"Reply-To": person.preferredemail.email}
            template = get_email_template('pending-membership-approval.txt')
        subject = "%s wants to join" % person.name
    else:
        raise AssertionError(
            "Unexpected membership status: %s" % membership.status)

    for address in admin_addrs:
        recipient = getUtility(IPersonSet).getByEmail(address)
        replacements['recipient_name'] = recipient.displayname
        msg = MailWrapper().format(
            template % replacements, force_wrap=True)
        simple_sendmail(from_addr, address, subject, msg, headers=headers)


def specification_notification_subject(spec):
    """Format the email subject line for a specification."""
    return '[Blueprint %s] %s' % (spec.name, spec.title)

@block_implicit_flushes
def notify_specification_modified(spec, event):
    """Notify the related people that a specification has been modifed."""
    user = IPerson(event.user)
    spec_delta = spec.getDelta(event.object_before_modification, user)
    if spec_delta is None:
        # XXX: Bjorn Tillenius 2006-03-08:
        #      Ideally, if an IObjectModifiedEvent event is generated,
        #      spec_delta shouldn't be None. I'm not confident that we
        #      have enough test yet to assert this, though.
        return

    subject = specification_notification_subject(spec)
    indent = ' '*4
    info_lines = []
    for dbitem_name in ('definition_status', 'priority'):
        title = ISpecification[dbitem_name].title
        assert ISpecification[dbitem_name].required, (
            "The mail notification assumes %s can't be None" % dbitem_name)
        dbitem_delta = getattr(spec_delta, dbitem_name)
        if dbitem_delta is not None:
            old_item = dbitem_delta['old']
            new_item = dbitem_delta['new']
            info_lines.append("%s%s: %s => %s" % (
                indent, title, old_item.title, new_item.title))

    for person_attrname in ('approver', 'assignee', 'drafter'):
        title = ISpecification[person_attrname].title
        person_delta = getattr(spec_delta, person_attrname)
        if person_delta is not None:
            old_person = person_delta['old']
            if old_person is None:
                old_value = "(none)"
            else:
                old_value = old_person.displayname
            new_person = person_delta['new']
            if new_person is None:
                new_value = "(none)"
            else:
                new_value = new_person.displayname
            info_lines.append(
                "%s%s: %s => %s" % (indent, title, old_value, new_value))

    mail_wrapper = MailWrapper(width=72)
    if spec_delta.whiteboard is not None:
        if info_lines:
            info_lines.append('')
        info_lines.append('Whiteboard changed to:')
        info_lines.append('')
        info_lines.append(mail_wrapper.format(spec_delta.whiteboard))

    if not info_lines:
        # The specification was modified, but we don't yet support
        # sending notification for the change.
        return
    body = get_email_template('specification-modified.txt') % {
        'editor': user.displayname,
        'info_fields': '\n'.join(info_lines),
        'spec_title': spec.title,
        'spec_url': canonical_url(spec)}

    for address in spec.notificationRecipientAddresses():
        simple_sendmail_from_person(user, address, subject, body)



@block_implicit_flushes
def notify_specification_subscription_created(specsub, event):
    """Notify a user that they have been subscribed to a blueprint."""
    user = IPerson(event.user)
    spec = specsub.specification
    person = specsub.person
    subject = specification_notification_subject(spec)
    mailwrapper = MailWrapper(width=72)
    body = mailwrapper.format(
        'You are now subscribed to the blueprint '
        '%(blueprint_name)s - %(blueprint_title)s.\n\n'
        '--\n  %(blueprint_url)s' %
        {'blueprint_name' : spec.name,
         'blueprint_title' : spec.title,
         'blueprint_url' : canonical_url(spec)})
    for address in get_contact_email_addresses(person):
        simple_sendmail_from_person(user, address, subject, body)

@block_implicit_flushes
def notify_specification_subscription_modified(specsub, event):
    """Notify a subscriber to a blueprint that their
    subscription has changed.
    """
    user = IPerson(event.user)
    spec = specsub.specification
    person = specsub.person
    # Only send a notification if the
    # subscription changed by someone else.
    if person == user:
        return
    subject = specification_notification_subject(spec)
    if specsub.essential:
        specsub_type = 'Participation essential'
    else:
        specsub_type = 'Participation non-essential'
    mailwrapper = MailWrapper(width=72)
    body = mailwrapper.format(
        'Your subscription to the blueprint '
        '%(blueprint_name)s - %(blueprint_title)s '
        'has changed to [%(specsub_type)s].\n\n'
        '--\n  %(blueprint_url)s' %
        {'blueprint_name' : spec.name,
         'blueprint_title' : spec.title,
         'specsub_type' : specsub_type,
         'blueprint_url' : canonical_url(spec)})
    for address in get_contact_email_addresses(person):
        simple_sendmail_from_person(user, address, subject, body)


def notify_mailinglist_activated(mailinglist, event):
    """Notification that a mailing list is available.

    All active members of a team and its subteams receive notification when
    the team's mailing list is available.
    """
    # We will use the setting of the date_activated field as a hint
    # that this list is new, and that noboby has subscribed yet.  See
    # `MailingList.transitionToStatus()` for the details.
    old_date = event.object_before_modification.date_activated
    new_date = event.object.date_activated
    list_looks_new = old_date is None and new_date is not None

    if not (list_looks_new and mailinglist.is_usable):
        return

    team = mailinglist.team
    from_address = format_address(
        team.displayname, config.canonical.noreply_from_address)
    headers = {}
    subject = "New Mailing List for %s" % team.displayname
    template = get_email_template('new-mailing-list.txt')
    editemails_url = '%s/+editemails'

    for person in team.allmembers:
        if person.is_team or person.preferredemail is None:
            # This is either a team or a person without a preferred email, so
            # don't send a notification.
            continue
        to_address = [str(person.preferredemail.email)]
        replacements = {
            'user': person.displayname,
            'team_displayname': team.displayname,
            'team_name': team.name,
            'team_url': canonical_url(team),
            'subscribe_url': editemails_url % canonical_url(person),
            }
        body = MailWrapper(72).format(template % replacements,
                                      force_wrap=True)
        simple_sendmail(from_address, to_address, subject, body, headers)


def notify_message_held(message_approval, event):
    """Send a notification of a message hold to all team administrators."""
    message_details = getAdapter(message_approval, IHeldMessageDetails)
    team = message_approval.mailing_list.team
    from_address = format_address(
        team.displayname, config.canonical.noreply_from_address)
    subject = (
        'New mailing list message requiring approval for %s'
        % team.displayname)
    template = get_email_template('new-held-message.txt')

    # Most of the replacements are the same for everyone.
    replacements = {
        'subject': message_details.subject,
        'author_name': message_details.author.displayname,
        'author_url': canonical_url(message_details.author),
        'date': message_details.date,
        'message_id': message_details.message_id,
        'review_url': '%s/+mailinglist-moderate' % canonical_url(team),
        'team': team.displayname,
        }

    # Send one message to every team administrator.
    person_set = getUtility(IPersonSet)
    for address in team.getTeamAdminsEmailAddresses():
        user = person_set.getByEmail(address)
        replacements['user'] = user.displayname
        body = MailWrapper(72).format(
            template % replacements, force_wrap=True)
        simple_sendmail(from_address, address, subject, body)


def encode(value):
    """Encode string for transport in a mail header.

    :param value: The raw email header value.
    :type value: unicode
    :return: The encoded header.
    :rtype: `email.Header.Header`
    """
    try:
        value.encode('us-ascii')
        charset = 'us-ascii'
    except UnicodeEncodeError:
        charset = 'utf-8'
    return Header(value.encode(charset), charset)


def send_direct_contact_email(
    sender_email, recipients_set, subject, body):
    """Send a direct user-to-user email.

    :param sender_email: The email address of the sender.
    :type sender_email: string
    :param recipients_set: The recipients.
    :type recipients_set:' A ContactViaWebNotificationSet
    :param subject: The Subject header.
    :type subject: unicode
    :param body: The message body.
    :type body: unicode
    :return: The sent message.
    :rtype: `email.Message.Message`
    """
    # Craft the email message.  Start by checking whether the subject and
    # message bodies are ASCII or not.
    subject_header = encode(subject)
    try:
        body.encode('us-ascii')
        charset = 'us-ascii'
    except UnicodeEncodeError:
        charset = 'utf-8'
    # Get the sender's real name, encoded as per RFC 2047.
    person_set = getUtility(IPersonSet)
    sender = person_set.getByEmail(sender_email)
    assert sender is not None, 'No person for sender %s' % sender_email
    sender_name = str(encode(sender.displayname))
    # Do a single authorization/quota check for the sender.  We consume one
    # quota credit per contact, not per recipient.
    authorization = IDirectEmailAuthorization(sender)
    if not authorization.is_allowed:
        raise QuotaReachedError(sender.displayname, authorization)
    # Add the footer as a unicode string, then encode the body if necessary.
    # This is not entirely optimal if the body has non-ascii characters in it,
    # since the footer may get garbled in a non-MIME aware mail reader.  Who
    # uses those anyway!?  The only alternative is to attach the footer as a
    # MIME attachment with a us-ascii charset, but that has it's own set of
    # problems (and user complaints).  Email sucks.
    additions = u'\n'.join([
        u'',
        u'-- ',
        u'This message was sent from Launchpad by the user',
        u'%s (%s)' % (sender_name , canonical_url(sender)),
        u'using %s.',
        u'For more information see',
        u'https://help.launchpad.net/YourAccount/ContactingPeople',
        ])
    # Craft and send one message per recipient.
    mailwrapper = MailWrapper(width=72)
    message = None
    for recipient_email, recipient in recipients_set.getRecipientPersons():
        recipient_name = str(encode(recipient.displayname))
        reason, rational_header = recipients_set.getReason(recipient_email)
        reason = str(encode(reason)).replace('\n ', '\n')
        formatted_body = mailwrapper.format(body, force_wrap=True)
        formatted_body += additions % reason
        formatted_body = formatted_body.encode(charset)
        message = MIMEText(formatted_body, _charset=charset)
        message['From'] = formataddr((sender_name, sender_email))
        message['To'] = formataddr((recipient_name, recipient_email))
        message['Subject'] = subject_header
        message['Message-ID'] = make_msgid('launchpad')
        message['X-Launchpad-Message-Rationale'] = rational_header
        # Send the message.
        sendmail(message, bulk=False)
    # BarryWarsaw 19-Nov-2008: If any messages were sent, record the fact that
    # the sender contacted the team.  This is not perfect though because we're
    # really recording the fact that the person contacted the last member of
    # the team.  There's little we can do better though because the team has
    # no contact address, and so there isn't actually an address to record as
    # the team's recipient.  It currently doesn't matter though because we
    # don't actually do anything with the recipient information yet.  All we
    # care about is the sender, for quota purposes.  We definitely want to
    # record the contact outside the above loop though, because if there are
    # 10 members of the team with no contact address, one message should not
    # consume the sender's entire quota.
    authorization.record(message)

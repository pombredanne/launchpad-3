# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Event handlers that send email notifications."""

__metaclass__ = type

from difflib import unified_diff
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEMessage import MIMEMessage
import re
import textwrap

from zope.component import getUtility
from zope.security.proxy import isinstance as zope_isinstance

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.interfaces import (
    IDistroBugTask, IDistroReleaseBugTask, ILanguageSet, IProductSeriesBugTask,
    ISpecification, ITeamMembershipSet, IUpstreamBugTask)
from canonical.launchpad.mail import (
    sendmail, simple_sendmail, simple_sendmail_from_person, format_address)
from canonical.launchpad.components.bug import BugDelta
from canonical.launchpad.components.bugtask import BugTaskDelta
from canonical.launchpad.helpers import (
    contactEmailAddresses, get_email_template)
from canonical.launchpad.webapp import canonical_url
from canonical.lp.dbschema import TeamMembershipStatus, TicketAction

GLOBAL_NOTIFICATION_EMAIL_ADDRS = []
CC = "CC"


class MailWrapper:
    """Wraps text that should be included in an email.

        :width: how long should the lines be
        :indent: specifies how much indentation the lines should have
        :indent_first_line: indicates whether the first line should be
                            indented or not.

    Note that MailWrapper doesn't guarantee that all lines will be less
    than :width:, sometimes it's better not to break long lines in
    emails. See textformatting.txt for more information.
    """

    def __init__(self, width=72, indent='', indent_first_line=True):
        self.indent = indent
        self.indent_first_line = indent_first_line
        self._text_wrapper = textwrap.TextWrapper(
            width=width, subsequent_indent=indent,
            replace_whitespace=False, break_long_words=False)

    def format(self, text):
        """Format the text to be included in an email."""
        wrapped_lines = []

        if self.indent_first_line:
            indentation = self.indent
        else:
            indentation = ''

        # We don't care about trailing whitespace.
        text = text.rstrip()

        # Normalize dos-style line endings to unix-style.
        text = text.replace('\r\n', '\n')

        for paragraph in text.split('\n\n'):
            lines = paragraph.split('\n')

            if len(lines) == 1:
                # We use TextWrapper only if the paragraph consists of a
                # single line, like in the case where a person enters a
                # comment via the web ui, without breaking the lines
                # manually.
                self._text_wrapper.initial_indent = indentation
                wrapped_lines += self._text_wrapper.wrap(paragraph)
            else:
                # If the user has gone through the trouble of wrapping
                # the lines, we shouldn't re-wrap them for him.
                wrapped_lines += (
                    [indentation + lines[0]] +
                    [self.indent + line for line in lines[1:]])

            if not self.indent_first_line:
                # 'indentation' was temporarily set to '' in order to
                # prevent the first line from being indented. Set it
                # back to self.indent so that the rest of the lines get
                # indented.
                indentation = self.indent

            # Add an empty line so that the paragraphs get separated by
            # a blank line when they are joined together again.
            wrapped_lines.append('')

        # We added one line too much, remove it.
        wrapped_lines = wrapped_lines[:-1]
        return '\n'.join(wrapped_lines)


def _send_bug_details_to_new_bugcontacts(
    bug, previous_subscribers, current_subscribers):
    """Send an email containing full bug details to new bug subscribers.

    This function is designed to handle situations where bugtasks get reassigned
    to new products or sourcepackages, and the new bugcontacts need to be
    notified of the bug.
    """
    prev_subs_set = set(previous_subscribers)
    cur_subs_set = set(current_subscribers)

    new_subs = cur_subs_set.difference(prev_subs_set)

    # Send a notification to the new bug contacts that weren't subscribed to the
    # bug before, which looks identical to a new bug report.
    subject, contents = generate_bug_add_email(bug)
    new_bugcontact_addresses = sorted([contactEmailAddresses(p) for p in new_subs])
    if new_bugcontact_addresses:
        send_bug_notification(
            bug=bug, user=bug.owner, subject=subject, contents=contents,
            to_addrs=new_bugcontact_addresses)


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
                new_product.security_contact)


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
    if failing_command is not None:
        failed_command_information = 'Failing command:\n    %s' % str(
            failing_command)
    else:
        failed_command_information = ''

    body = get_email_template('email-processing-error.txt') % {
            'failed_command_information': failed_command_information,
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
    # We add the error message in as a header too (X-Launchpad-Unhandled-Email)
    # so we can create filters in the Launchpad-Error-Reports Mailman
    # mailing list.
    simple_sendmail(
        get_bugmail_error_address(), [config.launchpad.errors_address],
        'Unhandled Email: %s' % file_alias_url,
        template % {'url': file_alias_url, 'error_msg': message},
        headers={'X-Launchpad-Unhandled-Email': message}
        )


def generate_bug_add_email(bug):
    """Generate a new bug notification from the given IBug.

    IBug is assumed to be a bug that was just added. The return value
    is (subject, body).
    """
    subject = u"[Bug %d] %s" % (bug.id, bug.title)

    if bug.private:
        # This is a confidential bug.
        visibility = u"Private"
    else:
        # This is a public bug.
        visibility = u"Public"

    bug_info = ''
    # Add information about the affected upstreams and packages.
    for bugtask in bug.bugtasks:
        bug_info += u"** Affects: %s\n" % bugtask.targetname
        bug_info += u"     Importance: %s\n" % bugtask.importance.title

        if bugtask.assignee:
            # There's a person assigned to fix this task, so show that
            # information too.
            bug_info += u"     Assignee: %s\n" % bugtask.assignee.displayname
        bug_info += u"         Status: %s\n" % bugtask.status.title

    mailwrapper = MailWrapper(width=72)
    contents = get_email_template('bug-add-notification-contents.txt') % {
        'visibility' : visibility, 'bugurl' : canonical_url(bug),
        'bug_info': bug_info,
        'description': mailwrapper.format(bug.description)}

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

    if bug_delta.title is not None:
        change_info = u"** Summary changed:\n\n"
        change_info += u"- %s\n" % bug_delta.title['old']
        change_info += u"+ %s" % bug_delta.title['new']
        changes.append(change_info)

    if bug_delta.description is not None:
        description_diff = get_unified_diff(
            bug_delta.description['old'],
            bug_delta.description['new'], 72)

        change_info = u"** Description changed:\n\n"
        change_info += description_diff
        changes.append(change_info)

    if bug_delta.private is not None:
        if bug_delta.private['new']:
            visibility = "Private"
        else:
            visibility = "Public"
        changes.append(u"** Visibility changed to: %s" % visibility)

    if bug_delta.security_related is not None:
        if bug_delta.security_related['new']:
            changes.append(u"** This bug has been flagged as a security issue")
        else:
            changes.append(
                u"** This bug is no longer flagged as a security issue")

    if bug_delta.tags is not None:
        new_tags = set(bug_delta.tags['new'])
        old_tags = set(bug_delta.tags['old'])
        added_tags = sorted(new_tags.difference(old_tags))
        removed_tags = sorted(old_tags.difference(new_tags))
        if added_tags:
            changes.append(u'** Tags added: %s' % ' '.join(added_tags))
        if removed_tags:
            changes.append(u'** Tags removed: %s' % ' '.join(removed_tags))

    if bug_delta.external_reference is not None:
        old_ext_ref = bug_delta.external_reference.get('old')
        if old_ext_ref is not None:
            changes.append(u'** Web link removed: %s' % old_ext_ref.url)
        new_ext_ref = bug_delta.external_reference['new']
        if new_ext_ref is not None:
            changes.append(u'** Web link added: %s' % new_ext_ref.url)

    if bug_delta.bugwatch is not None:
        old_bug_watch = bug_delta.bugwatch.get('old')
        if old_bug_watch:
            change_info = u"** Bug watch removed: %s #%s\n" % (
                old_bug_watch.bugtracker.title, old_bug_watch.remotebug)
            change_info += u"   %s" % old_bug_watch.url
            changes.append(change_info)
        new_bug_watch = bug_delta.bugwatch['new']
        if new_bug_watch:
            change_info = u"** Bug watch added: %s #%s\n" % (
                new_bug_watch.bugtracker.title, new_bug_watch.remotebug)
            change_info += u"   %s" % new_bug_watch.url
            changes.append(change_info)

    if bug_delta.cve is not None:
        new_cve = bug_delta.cve.get('new', None)
        old_cve = bug_delta.cve.get('old', None)
        if old_cve:
            changes.append(u"** CVE removed: %s" % old_cve.url)
        if new_cve:
            changes.append(u"** CVE added: %s" % new_cve.url)

    if bug_delta.attachment is not None and bug_delta.attachment['new']:
        added_attachment = bug_delta.attachment['new']
        change_info = '** Attachment added: "%s"\n' % added_attachment.title
        change_info += "   %s" % added_attachment.libraryfile.http_url
        changes.append(change_info)

    if bug_delta.bugtask_deltas is not None:
        bugtask_deltas = bug_delta.bugtask_deltas
        # Use zope_isinstance, to ensure that this Just Works with
        # security-proxied objects.
        if not zope_isinstance(bugtask_deltas, (list, tuple)):
            bugtask_deltas = [bugtask_deltas]
        for bugtask_delta in bugtask_deltas:
            change_info = u"** Changed in: %s\n" % (
                bugtask_delta.bugtask.targetname)

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
                    oldval_display = bugtask_delta.assignee['old'].browsername
                if bugtask_delta.assignee.get('new'):
                    newval_display = bugtask_delta.assignee['new'].browsername

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
                    added_bugtask.targetname)
                change_info += u"   %s\n" % added_bugtask.bugwatch.url
            else:
                change_info = u"** Also affects: %s\n" % (
                    added_bugtask.targetname)
            change_info += u"%13s: %s\n" % (u"Importance",
                added_bugtask.importance.title)
            if added_bugtask.assignee:
                assignee = added_bugtask.assignee
                change_info += u"%13s: %s <%s>\n" % (
                    u"Assignee", assignee.name, assignee.preferredemail.email)
            change_info += u"%13s: %s" % (u"Status", added_bugtask.status.title)
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


def send_bug_notification(bug, user, subject, contents, to_addrs=None,
                          headers=None):
    """Sends a bug notification.

    :bug: The bug the notification concerns.
    :user: The user that did that action that caused a notification to
           be sent.
    :subject: The subject of the notification.
    :contents: The content of the notification.
    :to_addrs: The addresses the notification should be sent to. If none
               are provided, the default bug cc list will be used.
    :headers: Any additional headers that should get added to the
              message.

    If no References header is given, one will be constructed to ensure
    that the notification gets grouped together with other notifications
    concerning the same bug (if the email client supports threading).
    """

    assert user is not None, 'user is None'

    if headers is None:
        headers = {}
    if to_addrs is None:
        to_addrs = get_cc_list(bug)

    if not to_addrs:
        # No recipients for this email means there's no point generating an
        # email.
        return

    if ('Message-Id' not in headers or
            headers['Message-Id'] != bug.initial_message.rfc822msgid):
        # It's not the initial, message. Let's add the inital message id
        # to the References header, so that it will be threaded properly.
        if not 'References' in headers:
            headers['References'] = ''
        references = headers['References'].split()
        if bug.initial_message.rfc822msgid not in references:
            references.insert(0, bug.initial_message.rfc822msgid)
        headers['References'] = ' '.join(references)

    # Use zope_isinstance, to ensure that this Just Works with
    # security-proxied objects.
    if not zope_isinstance(to_addrs, (list, tuple)):
        to_addrs = [to_addrs]

    if "Reply-To" not in headers:
        headers["Reply-To"] = get_bugmail_replyto_address(bug)

    # Add a header for each task on this bug, to help users organize
    # their incoming mail in a way that's convenient for them.
    x_launchpad_bug_values = []
    for bugtask in bug.bugtasks:
        x_launchpad_bug_values.append(bugtask.asEmailHeaderValue())

    headers["X-Launchpad-Bug"] = x_launchpad_bug_values

    body = get_email_template('bug-notification.txt') % {
        'content': contents,
        'bug_title': bug.title,
        'bug_url': canonical_url(bug)}

    for to_addr in to_addrs:
        simple_sendmail_from_person(
            person=user, to_addrs=to_addr, subject=subject,
            body=body, headers=headers)


def get_cc_list(bug):
    """Return the list of people that are CC'd on this bug.

    This also includes global subscribers, like the IRC bot.
    """
    subscriptions = []
    if not bug.private:
        subscriptions = list(GLOBAL_NOTIFICATION_EMAIL_ADDRS)

    subscriptions += bug.notificationRecipientAddresses()

    return subscriptions


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
        changes["bugurl"] = canonical_url(new_bug)
        changes["user"] = user

        return BugDelta(**changes)
    else:
        return None


def get_task_delta(old_task, new_task):
    """Compute the delta from old_task to new_task.

    old_task and new_task are either both IDistroBugTask's or both
    IUpstreamBugTask's, otherwise a TypeError is raised.

    Returns an IBugTaskDelta or None if there were no changes between
    old_task and new_task.
    """
    changes = {}
    if ((IUpstreamBugTask.providedBy(old_task) and
         IUpstreamBugTask.providedBy(new_task)) or
        (IProductSeriesBugTask.providedBy(old_task) and
         IProductSeriesBugTask.providedBy(new_task))):
        if old_task.product != new_task.product:
            changes["product"] = {}
            changes["product"]["old"] = old_task.product
            changes["product"]["new"] = new_task.product
    elif ((IDistroBugTask.providedBy(old_task) and
           IDistroBugTask.providedBy(new_task)) or
          (IDistroReleaseBugTask.providedBy(old_task) and
           IDistroReleaseBugTask.providedBy(new_task))):
        if old_task.sourcepackagename != new_task.sourcepackagename:
            changes["sourcepackagename"] = {}
            changes["sourcepackagename"]["old"] = old_task.sourcepackagename
            changes["sourcepackagename"]["new"] = new_task.sourcepackagename
    else:
        raise TypeError(
            "Can't calculate delta on bug tasks of incompatible types: "
            "[%s, %s]" % (repr(old_task), repr(new_task)))

    # calculate the differences in the fields that both types of tasks
    # have in common
    for field_name in ("status", "importance",
                       "assignee", "bugwatch", "milestone"):
        old_val = getattr(old_task, field_name)
        new_val = getattr(new_task, field_name)
        if old_val != new_val:
            changes[field_name] = {}
            changes[field_name]["old"] = old_val
            changes[field_name]["new"] = new_val

    if changes:
        changes["bugtask"] = old_task
        return BugTaskDelta(**changes)
    else:
        return None


def notify_bug_added(bug, event):
    """Send an email notification that a bug was added.

    Event must be an ISQLObjectCreatedEvent.
    """

    bug.addCommentNotification(bug.initial_message)


def notify_bug_modified(modified_bug, event):
    """Notify the Cc'd list that this bug has been modified.

    modified_bug bug must be an IBug. event must be an
    ISQLObjectModifiedEvent.
    """
    bug_delta = get_bug_delta(
        old_bug=event.object_before_modification,
        new_bug=event.object, user=event.user)

    assert bug_delta is not None

    add_bug_change_notifications(bug_delta)


def add_bug_change_notifications(bug_delta):
    """Generate bug notifications and add them to the bug."""
    changes = get_bug_edit_notification_texts(bug_delta)
    for text_change in changes:
        bug_delta.bug.addChangeNotification(text_change, person=bug_delta.user)


def notify_bugtask_added(bugtask, event):
    """Notify CC'd list that this bug has been marked as needing fixing
    somewhere else.

    bugtask must be in IBugTask. event must be an
    ISQLObjectModifiedEvent.
    """
    bugtask = event.object

    bug_delta = BugDelta(
        bug=bugtask.bug,
        bugurl=canonical_url(bugtask.bug),
        user=event.user,
        added_bugtasks=bugtask)

    add_bug_change_notifications(bug_delta)


def notify_bugtask_edited(modified_bugtask, event):
    """Notify CC'd subscribers of this bug that something has changed
    on this task.

    modified_bugtask must be an IBugTask. event must be an
    ISQLObjectModifiedEvent.
    """
    bugtask_delta = get_task_delta(
        event.object_before_modification, event.object)
    bug_delta = BugDelta(
        bug=event.object.bug,
        bugurl=canonical_url(event.object.bug),
        bugtask_deltas=bugtask_delta,
        user=event.user)

    add_bug_change_notifications(bug_delta)

    previous_subscribers = event.object_before_modification.bug_subscribers
    current_subscribers = event.object.bug_subscribers
    _send_bug_details_to_new_bugcontacts(
        event.object.bug, previous_subscribers, current_subscribers)
    update_security_contact_subscriptions(modified_bugtask, event)


def notify_bug_comment_added(bugmessage, event):
    """Notify CC'd list that a message was added to this bug.

    bugmessage must be an IBugMessage. event must be an
    ISQLObjectCreatedEvent. If bugmessage.bug is a duplicate the
    comment will also be sent to the dup target's subscribers.
    """
    bug = bugmessage.bug
    bug.addCommentNotification(bugmessage.message)


def notify_bug_external_ref_added(ext_ref, event):
    """Notify CC'd list that a new web link has been added for this
    bug.

    ext_ref must be an IBugExternalRef. event must be an
    ISQLObjectCreatedEvent.
    """
    bug_delta = BugDelta(
        bug=ext_ref.bug,
        bugurl=canonical_url(ext_ref.bug),
        user=event.user,
        external_reference={'new' : ext_ref})

    add_bug_change_notifications(bug_delta)


def notify_bug_external_ref_edited(edited_ext_ref, event):
    """Notify CC'd list that a web link has been edited.

    edited_ext_ref must be an IBugExternalRef. event must be an
    ISQLObjectModifiedEvent.
    """
    old = event.object_before_modification
    new = event.object
    if ((old.url != new.url) or (old.title != new.title)):
        # A change was made that's worth sending an edit
        # notification about.
        bug_delta = BugDelta(
            bug=new.bug,
            bugurl=canonical_url(new.bug),
            user=event.user,
            external_reference={'old' : old, 'new' : new})

        add_bug_change_notifications(bug_delta)


def notify_bug_watch_added(watch, event):
    """Notify CC'd list that a new watch has been added for this bug.

    watch must be an IBugWatch. event must be an
    ISQLObjectCreatedEvent.
    """
    bug_delta = BugDelta(
        bug=watch.bug,
        bugurl=canonical_url(watch.bug),
        user=event.user,
        bugwatch={'new' : watch})

    add_bug_change_notifications(bug_delta)


def notify_bug_watch_modified(modified_bug_watch, event):
    """Notify CC'd bug subscribers that a bug watch was edited.

    modified_bug_watch must be an IBugWatch. event must be an
    ISQLObjectModifiedEvent.
    """
    old = event.object_before_modification
    new = event.object
    if ((old.bugtracker != new.bugtracker) or
        (old.remotebug != new.remotebug)):
        # there is a difference worth notifying about here
        # so let's keep going
        bug_delta = BugDelta(
            bug=new.bug,
            bugurl=canonical_url(new.bug),
            user=event.user,
            bugwatch={'old' : old, 'new' : new})

        add_bug_change_notifications(bug_delta)


def notify_bug_cve_added(bugcve, event):
    """Notify CC'd list that a new cve ref has been added to this bug.

    bugcve must be an IBugCve. event must be an ISQLObjectCreatedEvent.
    """
    bug_delta = BugDelta(
        bug=bugcve.bug,
        bugurl=canonical_url(bugcve.bug),
        user=event.user,
        cve={'new': bugcve.cve})

    add_bug_change_notifications(bug_delta)

def notify_bug_cve_deleted(bugcve, event):
    """Notify CC'd list that a cve ref has been removed from this bug.

    bugcve must be an IBugCve. event must be an ISQLObjectDeletedEvent.
    """
    bug_delta = BugDelta(
        bug=bugcve.bug,
        bugurl=canonical_url(bugcve.bug),
        user=event.user,
        cve={'old': bugcve.cve})

    add_bug_change_notifications(bug_delta)


def notify_bug_attachment_added(bugattachment, event):
    """Notify CC'd list that a new attachment has been added.

    bugattachment must be an IBugAttachment. event must be an
    ISQLObjectCreatedEvent.
    """
    bug = bugattachment.bug
    bug_delta = BugDelta(
        bug=bug,
        bugurl=canonical_url(bug),
        user=event.user,
        attachment={'new' : bugattachment})

    add_bug_change_notifications(bug_delta)


def notify_team_join(event):
    """Notify team administrators that a new joined (or tried to) the team.

    If the team's policy is Moderated, the email will say that the membership
    is pending approval. Otherwise it'll say that the user has joined the team
    and who added that person to the team.
    """
    user = event.user
    team = event.team
    membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(user, team)
    assert membership is not None
    reviewer = membership.reviewer
    approved, admin = [
        TeamMembershipStatus.APPROVED, TeamMembershipStatus.ADMIN]
    admin_addrs = team.getTeamAdminsEmailAddresses()

    from_addr = format_address('Launchpad', config.noreply_from_address)

    if reviewer != user and membership.status in [approved, admin]:
        # Somebody added this user as a member, we better send a notification
        # to the user too.
        member_addrs = contactEmailAddresses(user)

        subject = (
            'Launchpad: %s is now a member of %s' % (user.name, team.name))
        if user.isTeam():
            templatename = 'new-member-notification-for-teams.txt'
        else:
            templatename = 'new-member-notification.txt'

        template = get_email_template(templatename)
        msg = template % {
            'reviewer': '%s (%s)' % (reviewer.browsername, reviewer.name),
            'member': '%s (%s)' % (user.browsername, user.name),
            'team': '%s (%s)' % (team.browsername, team.name)}
        msg = MailWrapper().format(msg)
        simple_sendmail(from_addr, member_addrs, subject, msg)

        # The member's email address may be in admin_addrs too; let's remove
        # it so the member don't get two notifications.
        admin_addrs = set(admin_addrs).difference(set(member_addrs))

    # Yes, we can have teams with no members; not even admins.
    if not admin_addrs:
        return

    replacements = {
        'person_name': "%s (%s)" % (user.browsername, user.name),
        'team_name': "%s (%s)" % (team.browsername, team.name),
        'reviewer_name': "%s (%s)" % (reviewer.browsername, reviewer.name),
        'url': canonical_url(membership)}

    headers = {}
    if membership.status in [approved, admin]:
        template = get_email_template('new-member-notification-for-admins.txt')
        subject = (
            'Launchpad: %s is now a member of %s' % (user.name, team.name))
    else:
        template = get_email_template('pending-membership-approval.txt')
        subject = (
            "Launchpad: %s wants to join team %s" % (user.name, team.name))
        headers = {"Reply-To": user.preferredemail.email}

    msg = MailWrapper().format(template % replacements)
    simple_sendmail(from_addr, admin_addrs, subject, msg, headers=headers)


class TicketNotification:
    """Base class for a notification related to a ticket.

    Creating an instance of that class will build the notification and
    send it to the appropriate recipients. That way, subclasses of
    TicketNotification can be registered as event subscribers.
    """

    def __init__(self, ticket, event):
        """Base constructor.

        It saves the ticket and event in attributes and then call
        the initialize() and send() method.
        """
        self.ticket = ticket
        self.event = event
        self.initialize()
        if self.shouldNotify():
            self.send()

    def getFromAddress(self):
        """Return a formatted email address suitable for user in the From
        header of the ticket notification.

        Default is Event Person Display Name <ticket#@tickettracker_domain>
        """
        return format_address(
            self.event.user.displayname,
            'ticket%s@%s' % (
                self.ticket.id, config.tickettracker.email_domain))

    def getSubject(self):
        """Return the subject of the notification.

        Default to [Support #dd]: Title
        """
        return '[Support #%s]: %s' % (self.ticket.id, self.ticket.title)

    def getBody(self):
        """Return the content of the notification message.

        This method must be implemented by a subclass.
        """
        raise NotImplementedError

    def getRecipients(self):
        """Return the recipient of the notification.

        Default to the ticket's subscribers that speaks the request languages.
        If the ticket owner is subscribed, he's always consider to speak the
        language. When a subscriber is a team and it doesn't have an email
        set nor supported languages, only contacts the members that speaks
        the supported language.
        """
        # Optimize the English case.
        english = getUtility(ILanguageSet)['en']
        ticket_language = self.ticket.language
        if ticket_language == english:
            return self.ticket.getSubscribers()

        recipients = set()
        skipped = set()
        subscribers = set(self.ticket.getSubscribers())
        while subscribers:
            person = subscribers.pop()
            if person == self.ticket.owner:
                recipients.add(person)
            elif ticket_language not in person.getSupportedLanguages():
               skipped.add(person)
            elif not person.preferredemail and not list(person.languages):
                # For teams without an email address nor a set of supported
                # languages, only notify the members that actually speak the
                # language.
                subscribers |= set(person.activemembers) - recipients - skipped
            else:
                recipients.add(person)
        return recipients

    def initialize(self):
        """Initialization hook for subclasses.

        This method is called before send() and can be use for any
        setup purpose.

        Default does nothing.
        """
        pass

    def shouldNotify(self):
        """Return if there is something to notify about.

        When this method returns False, no notification will be sent.
        By default, all event trigger a notification.
        """
        return True

    def send(self):
        """Sends the notification to all the notification recipients."""
        sent_addrs = set()
        from_address = self.getFromAddress()
        subject = self.getSubject()
        body = self.getBody()
        for notified_person in self.getRecipients():
            for address in contactEmailAddresses(notified_person):
                if address not in sent_addrs:
                    simple_sendmail(
                        from_address, address, subject, body)
                    sent_addrs.add(address)

    @property
    def unsupported_language(self):
        """Whether the ticket language is unsupported or not."""
        supported_languages = self.ticket.target.getSupportedLanguages()
        return self.ticket.language not in supported_languages

    @property
    def unsupported_language_warning(self):
        """Warning about the fact that the ticket is written in an
        unsupported language."""
        return get_email_template(
                'ticket-unsupported-language-warning.txt') % {
                'ticket_language': self.ticket.language.englishname,
                'target_name': self.ticket.target.displayname}


class TicketAddedNotification(TicketNotification):
    """Notification sent when a ticket is added."""

    def getBody(self):
        """See TicketNotification."""
        ticket = self.ticket
        body = get_email_template('ticket_added.txt') % {
            'target_name': ticket.target.displayname,
            'ticket_id': ticket.id,
            'ticket_url': canonical_url(ticket),
            'comment': ticket.description}
        if self.unsupported_language:
            body += self.unsupported_language_warning
        return body


class TicketModifiedDefaultNotification(TicketNotification):
    """Base implementation of a notification when a ticket is modified."""

    # Email template used to render the body.
    body_template = "ticket_modified.txt"

    def initialize(self):
        """Save the old ticket for comparison. It also set the new_message
        attribute if a new message was added.
        """
        self.old_ticket = self.event.object_before_modification

        new_messages = set(
            self.ticket.messages).difference(self.old_ticket.messages)
        assert len(new_messages) <= 1, (
                "There shouldn't be more than one message for a notification.")
        if new_messages:
            self.new_message = new_messages.pop()
        else:
            self.new_message = None

        self.wrapper = MailWrapper()

    @cachedproperty
    def metadata_changes_text(self):
        """Textual representation of the changes to the ticket metadata."""
        ticket = self.ticket
        old_ticket = self.old_ticket
        indent = 4*' '
        info_fields = []
        if ticket.status != old_ticket.status:
            info_fields.append(indent + 'Status: %s => %s' % (
                old_ticket.status.title, ticket.status.title))

        old_bugs = set(old_ticket.bugs)
        bugs = set(ticket.bugs)
        for linked_bug in bugs.difference(old_bugs):
            info_fields.append(
                indent + 'Linked to bug: #%s\n' % linked_bug.id +
                indent + canonical_url(linked_bug))
        for unlinked_bug in old_bugs.difference(bugs):
            info_fields.append(
                indent + 'Removed link to bug: #%s\n' % unlinked_bug.id +
                indent + canonical_url(unlinked_bug))

        if ticket.title != old_ticket.title:
            info_fields.append('Summary changed to:\n%s' % ticket.title)
        if ticket.description != old_ticket.description:
            info_fields.append(
                'Description changed to:\n%s' % (
                    self.wrapper.format(ticket.description)))

        ticket_changes = '\n\n'.join(info_fields)
        return ticket_changes

    def getSubject(self):
        """When a comment is added, its title is used as the subject,
        otherwise the ticket title is used.
        """
        prefix = '[Support #%s]: ' % self.ticket.id
        if self.new_message:
            subject = self.new_message.subject
            if prefix in self.new_message.subject:
                return subject
            elif subject[0:4] in ['Re: ', 'RE: ']:
                # Place prefix after possible reply prefix.
                return subject[0:4] + prefix + subject[4:]
            else:
                return prefix + subject
        else:
            return prefix + self.ticket.title

    def shouldNotify(self):
        """Only send a notification when a message was added or some
        metadata was changed.
        """
        return self.new_message or self.metadata_changes_text

    def getBody(self):
        """See TicketNotification."""
        body = self.metadata_changes_text
        replacements = dict(
            ticket_id=self.ticket.id,
            target_name=self.ticket.target.displayname,
            ticket_url=canonical_url(self.ticket))

        if self.new_message:
            if body:
                body += '\n\n'
            body += self.getNewMessageText()
            replacements['new_message_id'] = list(
                self.ticket.messages).index(self.new_message)

        replacements['body'] = body

        return get_email_template(self.body_template) % replacements

    def getRecipients(self):
        """The default notification goes to all ticket susbcribers that
        speaks the request language, except the owner.
        """
        return [person for person in TicketNotification.getRecipients(self)
                if person != self.ticket.owner]

    # Header template used when a new message is added to the ticket.
    action_header_template = {
        TicketAction.REQUESTINFO:
            '%(person)s requested for more information:',
        TicketAction.CONFIRM:
            '%(person)s confirmed that the request is solved:',
        TicketAction.COMMENT:
            '%(person)s posted a new comment:',
        TicketAction.GIVEINFO:
            '%(person)s gave more information on the request:',
        TicketAction.REOPEN:
            '%(person)s is still having a problem:',
        TicketAction.ANSWER:
            '%(person)s proposed the following answer:',
        TicketAction.EXPIRE:
            '%(person)s expired the request:',
        TicketAction.REJECT:
            '%(person)s rejected the request:',
        TicketAction.SETSTATUS:
            '%(person)s changed the request status:',
    }

    def getNewMessageText(self):
        """Should return the notification text related to a new message."""
        if not self.new_message:
            return ''

        header = self.action_header_template.get(
            self.new_message.action, '%(person)s posted a new message:') % {
            'person': self.new_message.owner.displayname}

        return '\n'.join([
            header, self.wrapper.format(self.new_message.text_contents)])


class TicketModifiedOwnerNotification(TicketModifiedDefaultNotification):
    """Notification sent to the owner when his ticket is modified."""

    # These actions will be done by the owner, so use the second person.
    action_header_template = dict(
        TicketModifiedDefaultNotification.action_header_template)
    action_header_template.update({
        TicketAction.CONFIRM:
            'You confirmed that the request is solved:',
        TicketAction.GIVEINFO:
            'You gave more information on the request:',
        TicketAction.REOPEN:
            'You are still having a problem:',
        })

    body_template = 'ticket-modified-owner-notification.txt'

    body_template_by_action = {
        TicketAction.ANSWER: "ticket-answered-owner-notification.txt",
        TicketAction.EXPIRE: "ticket-expired-owner-notification.txt",
        TicketAction.REJECT: "ticket-rejected-owner-notification.txt",
        TicketAction.REQUESTINFO: (
            "ticket-info-requested-owner-notification.txt"),
    }

    def initialize(self):
        """Set the template that will be used based on the new comment action."""
        TicketModifiedDefaultNotification.initialize(self)
        if self.new_message:
            self.body_template = self.body_template_by_action.get(
                self.new_message.action, self.body_template)

    def getRecipients(self):
        """Return the owner of the ticket if he's still subscribed."""
        if self.ticket.isSubscribed(self.ticket.owner):
            return [self.ticket.owner]
        else:
            return []

    def getBody(self):
        """See TicketNotification."""
        body = TicketModifiedDefaultNotification.getBody(self)
        if self.unsupported_language:
            body += self.unsupported_language_warning
        return body


class TicketUnsupportedLanguageNotification(TicketNotification):
    """Notification sent to support contacts for unsupported languages."""

    def getSubject(self):
        """See TicketNotification."""
        return '[Support #%s]: (%s) %s' % (
            self.ticket.id, self.ticket.language.englishname,
            self.ticket.title)

    def shouldNotify(self):
        return self.unsupported_language

    def getRecipients(self):
        """Notify all the support contacts."""
        return self.ticket.target.support_contacts

    def getBody(self):
        """See TicketNotification."""
        ticket = self.ticket
        return get_email_template('ticket-unsupported-languages-added.txt') % {
            'target_name': ticket.target.displayname,
            'ticket_id': ticket.id,
            'ticket_url': canonical_url(ticket),
            'ticket_language': ticket.language.englishname,
            'comment': ticket.description}


def notify_specification_modified(spec, event):
    """Notify the related people that a specification has been modifed."""
    spec_delta = spec.getDelta(event.object_before_modification, event.user)
    if spec_delta is None:
        #XXX: Ideally, if an ISQLObjectModifiedEvent event is generated,
        #     spec_delta shouldn't be None. I'm not confident that we
        #     have enough test yet to assert this, though.
        #     -- Bjorn Tillenius, 2006-03-08
        return

    subject = '[Spec %s] %s' % (spec.name, spec.title)
    indent = ' '*4
    info_lines = []
    for dbitem_name in ('status', 'priority'):
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
        'editor': event.user.displayname,
        'info_fields': '\n'.join(info_lines),
        'spec_title': spec.title,
        'spec_url': canonical_url(spec)}

    for address in spec.notificationRecipientAddresses():
        simple_sendmail_from_person(event.user, address, subject, body)

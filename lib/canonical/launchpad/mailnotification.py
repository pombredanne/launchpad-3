# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Event handlers that send email notifications."""

__metaclass__ = type

import itertools
import sets
import textwrap

from zope.security.proxy import isinstance as zope_isinstance

from canonical.config import config
from canonical.launchpad.interfaces import (
    IBugDelta, IDistroBugTask, IDistroReleaseBugTask, IRemoteBugTask, 
    ISpecification, IUpstreamBugTask)
from canonical.launchpad.mail import (
    simple_sendmail, simple_sendmail_from_person, format_address)
from canonical.launchpad.components.bug import BugDelta
from canonical.launchpad.components.bugtask import BugTaskDelta
from canonical.launchpad.helpers import (
    contactEmailAddresses, get_email_template)
from canonical.launchpad.webapp import canonical_url

GLOBAL_NOTIFICATION_EMAIL_ADDRS = ("dilys@muse.19inch.net",)
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


def update_bug_contact_subscriptions(modified_bugtask, event):
    """Modify the bug Cc list when a bugtask is retargeted."""
    bugtask_before_modification = event.object_before_modification
    bugtask_after_modification = event.object

    # We don't make any changes to subscriber lists on private bugs.
    if bugtask_after_modification.bug.private:
        return

    # Calculate the list of new bug contacts, if any.
    new_bugcontacts = []
    if IUpstreamBugTask.providedBy(modified_bugtask):
        if (bugtask_before_modification.product !=
            bugtask_after_modification.product):
            if bugtask_after_modification.product.bugcontact:
                new_bugcontacts.append(
                    bugtask_after_modification.product.bugcontact)
    elif (IDistroBugTask.providedBy(modified_bugtask) or
          IDistroReleaseBugTask.providedBy(modified_bugtask)):
        if bugtask_after_modification.sourcepackagename is None:
            # No new bug contacts to be subscribed.
            return
        if (bugtask_before_modification.sourcepackagename !=
            bugtask_after_modification.sourcepackagename):
            new_sourcepackage = (
                bugtask_after_modification.distribution.getSourcePackage(
                bugtask_after_modification.sourcepackagename.name))
            for package_bug_contact in new_sourcepackage.bugcontacts:
                new_bugcontacts.append(package_bug_contact.bugcontact)

    # Subscribe all the new bug contacts for the new package or product if they
    # aren't already subscribed to this bug.
    bug = bugtask_after_modification.bug
    old_cc_list = get_cc_list(bug)
    new_bugcontact_addresses = set()
    for bugcontact in new_bugcontacts:
        if not bug.isSubscribed(bugcontact):
            bug.subscribe(bugcontact)
            new_bugcontact_addresses.update(contactEmailAddresses(bugcontact))

    # Send a notification to the new bug contacts that weren't
    # subscribed to the bug before, which looks identical to a new bug
    # report.
    subject, body = generate_bug_add_email(bug)
    new_bugcontact_addresses.difference_update(old_cc_list)
    if new_bugcontact_addresses:
        send_bug_notification(
            bug=bug, user=bug.owner, subject=subject, body=body,
            to_addrs=new_bugcontact_addresses)


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


def send_process_error_notification(to_addrs, subject, error_msg, 
                                    failing_command=None):
    """Sends an error message.

    Tells the user that an error was encountered while processing
    his request.

        :to_addrs: The addresses to send the notification to.
        :subject: The subject ot the notification.
        :error_msg: The error message that explains the error.
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
    simple_sendmail(get_bugmail_error_address(), to_addrs, subject, body)


def notify_errors_list(message, file_alias_url):
    """Sends an error to the Launchpad errors list."""
    template = get_email_template('notify-unhandled-email.txt')
    simple_sendmail(
        get_bugmail_error_address(), [config.launchpad.errors_address],
        'Unhandled Email: %s' % file_alias_url,
        template % {'url': file_alias_url, 'error_msg': message})


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

    body = (u"%(visibility)s bug reported:\n"
            u"%(bugurl)s\n\n"
            % {'visibility' : visibility, 'bugurl' : canonical_url(bug)})

    # Add information about the affected upstreams and packages.
    for bugtask in bug.bugtasks:
        body += u"Affects: %s\n" % bugtask.targetname
        body += u"       Severity: %s\n" % bugtask.severity.title

        if bugtask.priority:
            priority = bugtask.priority.title
        else:
            priority = "(none set)"
        body += u"       Priority: %s\n" % priority

        if bugtask.assignee:
            # There's a person assigned to fix this task, so show that
            # information too.
            body += u"       Assignee: %s\n" % bugtask.assignee.displayname
        body += u"         Status: %s\n" % bugtask.status.title

    # Add the description.
    body += u"\n"
    mailwrapper = MailWrapper(width=72)
    body += u"Description:\n%s" % mailwrapper.format(bug.description)

    body = body.rstrip()

    return (subject, body)


def generate_bug_edit_email(bug_delta):
    """Generate a bug edit notification based on the bug_delta.

    bug_delta is an object that provides IBugDelta. The return value
    is (subject, body).
    """
    subject = u"[Bug %d] %s" % (bug_delta.bug.id, bug_delta.bug.title)

    mailwrapper = MailWrapper(width=72, indent=u"    ")

    if bug_delta.bug.private:
        visibility = u"Private"
    else:
        visibility = u"Public"

    body = (u"%(visibility)s bug report changed:\n"
            u"%(bugurl)s\n\n"
            % {'visibility' : visibility, 'bugurl' : bug_delta.bugurl})

    # figure out what's been changed; add that information to the
    # email as appropriate
    if bug_delta.duplicateof is not None:
        new_bug_dupe = bug_delta.duplicateof['new']
        old_bug_dupe = bug_delta.duplicateof['old']
        assert new_bug_dupe is not None or old_bug_dupe is not None
        assert new_bug_dupe != old_bug_dupe
        if old_bug_dupe is not None:
            body += (
                u"*** This bug is no longer a duplicate of bug %d ***\n\n" %
                old_bug_dupe.id)
        if new_bug_dupe is not None:
            body += (
                u"*** This bug has been marked a duplicate of bug %d ***\n\n" %
                new_bug_dupe.id)

    if bug_delta.title is not None:
        body += u"Summary changed to:\n"
        body += u"    %s\n" % bug_delta.title

    if bug_delta.description is not None:
        body += u"Description changed to:\n"
        body += mailwrapper.format(bug_delta.description)
        body += u"\n"

    if bug_delta.private is not None:
        body += u"Visibility changed to:\n"
        if bug_delta.private['new']:
            body += u"    Private\n"
        else:
            body += u"    Public\n"

    if bug_delta.external_reference is not None:
        new_ext_ref = bug_delta.external_reference['new']
        body += u"Web links changed:\n"
        body += u"    + %s (%s)\n" % (new_ext_ref.url, new_ext_ref.title)
        old_ext_ref = bug_delta.external_reference.get('old')
        if old_ext_ref is not None:
            body += u"    - %s (%s)\n" % (old_ext_ref.url, old_ext_ref.title)

    if bug_delta.bugwatch is not None:
        new_bugwatch = bug_delta.bugwatch['new']
        body += u"Bug watches changed:\n"
        body += u"    + Bug %s [%s]\n" % (
            new_bugwatch.remotebug, new_bugwatch.bugtracker.title)
        old_bug_watch = bug_delta.bugwatch.get('old')
        if old_bug_watch:
            body += u"    - Bug %s [%s]\n" % (
                old_bug_watch.remotebug, old_bug_watch.bugtracker.title)

    if bug_delta.cve is not None:
        new_cve = bug_delta.cve.get('new', None)
        old_cve = bug_delta.cve.get('old', None)
        body += u""
        if new_cve:
            body += u"Added %s\n" % new_cve.title
        if old_cve:
            body += u"Removed %s\n" % old_cve.title

    if bug_delta.attachment is not None:
        body += "    - Changed attachments:\n"
        body += "        Added: %s\n" % (
            bug_delta.attachment['new'].title)
        body += "           %s\n" % (
            bug_delta.attachment['new'].libraryfile.url)
        old_attachment = bug_delta.attachment.get('old')
        if old_attachment:
            body += "      Removed: %s\n" % old_attachment.title

    if bug_delta.bugtask_deltas is not None:
        bugtask_deltas = bug_delta.bugtask_deltas
        # Use zope_isinstance, to ensure that this Just Works with
        # security-proxied objects.
        if not zope_isinstance(bugtask_deltas, (list, tuple)):
            bugtask_deltas = [bugtask_deltas]
        for bugtask_delta in bugtask_deltas:
            if not body[-2:] == u"\n\n":
                body += u"\n"

            if IUpstreamBugTask.providedBy(bugtask_delta.bugtask):
                body += u"Changed in: %s (upstream)\n" % (
                    bugtask_delta.bugtask.product.displayname)
            else:
                if IDistroBugTask.providedBy(bugtask_delta.bugtask):
                    distro_or_distrorelease_name = \
                        bugtask_delta.bugtask.distribution.name
                elif IDistroReleaseBugTask.providedBy(bugtask_delta.bugtask):
                    distro_or_distrorelease_name = u"%s %s" % (
                        bugtask_delta.bugtask.distrorelease.distribution.name,
                        bugtask_delta.bugtask.distrorelease.name)
                else:
                    raise ValueError(
                        "BugTask of unknown type: %s. Must provide "
                        "IUpstreamBugTask, IDistroBugTask or "
                        "IDistroReleaseBugTask." % str(bugtask_delta.bugtask))

                spname = None
                if (bugtask_delta.sourcepackagename is not None and
                    bugtask_delta.sourcepackagename.get("old") is not None):
                    spname = bugtask_delta.sourcepackagename["old"].name
                else:
                    if bugtask_delta.bugtask.sourcepackagename is not None:
                        spname = bugtask_delta.bugtask.sourcepackagename.name

                if spname:
                    body += u"Task: %s %s\n" % (
                        distro_or_distrorelease_name, spname)
                else:
                    body += u"Task: %s\n" % distro_or_distrorelease_name

            for fieldname, displayattrname in (
                ("product", "displayname"), ("sourcepackagename", "name"),
                ("binarypackagename", "name"), ("severity", "title"),
                ("priority", "title"), ("bugwatch", "title")):
                change = getattr(bugtask_delta, fieldname)
                if change:
                    oldval_display, newval_display = _get_task_change_values(
                        change, displayattrname)
                    body += _get_task_change_row(
                        fieldname, oldval_display, newval_display)

            if bugtask_delta.assignee is not None:
                oldval_display = u"(unassigned)"
                newval_display = u"(unassigned)"
                if bugtask_delta.assignee.get('old'):
                    oldval_display = bugtask_delta.assignee['old'].browsername
                if bugtask_delta.assignee.get('new'):
                    newval_display = bugtask_delta.assignee['new'].browsername

                changerow = (
                    u"%(label)15s: %(oldval)s => %(newval)s\n" % {
                    'label' : u"Assignee", 'oldval' : oldval_display,
                    'newval' : newval_display})
                body += changerow

            for fieldname, displayattrname in (
                ("status", "title"), ("target", "name")):
                change = getattr(bugtask_delta, fieldname)
                if change:
                    oldval_display, newval_display = _get_task_change_values(
                        change, displayattrname)
                    body += _get_task_change_row(
                        fieldname, oldval_display, newval_display)

    if bug_delta.added_bugtasks is not None:
        if not body[-2:] == u"\n\n":
            body += u"\n"

        # Use zope_isinstance, to ensure that this Just Works with
        # security-proxied objects.
        if zope_isinstance(bug_delta.added_bugtasks, (list, tuple)):
            added_bugtasks = bug_delta.added_bugtasks
        else:
            added_bugtasks = [bug_delta.added_bugtasks]

        for added_bugtask in added_bugtasks:
            body += u"Also affects: %s\n" % added_bugtask.targetname
            body += u"%15s: %s\n" % (u"Severity", added_bugtask.severity.title)
            if added_bugtask.priority:
                priority_title = added_bugtask.priority.title
            else:
                priority_title = "(none set)"
            body += u"%15s: %s\n" % (u"Priority", priority_title)
            if added_bugtask.assignee:
                assignee = added_bugtask.assignee
                body += u"%15s: %s <%s>\n" % (
                    u"Assignee", assignee.name, assignee.preferredemail.email)
            body += u"%15s: %s" % (u"Status", added_bugtask.status.title)

    body = body.rstrip()

    if bug_delta.comment_on_change:
        comment_wrapper = MailWrapper(width=72)
        body += "\n\nComment:\n"
        body += comment_wrapper.format(bug_delta.comment_on_change)

    return (subject, body)


def generate_bug_comment_email(bug_comment):
    """Generate a bug comment notification from bug_comment.

    bug_comment is expected to provide IBugMessage. The return value is
    (subject, body).
    """
    subject = u"[Bug %d] %s" % (bug_comment.bug.id, bug_comment.bug.title)
    bug = bug_comment.bug
    if bug.private:
        # This is a confidential bug.
        visibility = u"Private"
    else:
        # This is a public bug.
        visibility = u"Public"

    comment_wrapper = MailWrapper(width=72)

    body = (u"%(visibility)s bug report changed:\n"
            u"%(bugurl)s\n\n"
            u"Comment:\n"
            u"%(comment)s"
            % {'visibility' : visibility, 'bugurl' : canonical_url(bug),
               'comment' : comment_wrapper.format(
                    bug_comment.message.text_contents)})

    body = body.rstrip()

    return (subject, body)


def _get_task_change_row(label, oldval_display, newval_display):
    """Return a row formatted for display in task change info."""
    return u"%(label)15s: %(oldval)s => %(newval)s\n" % {
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


def send_bug_notification(bug, user, subject, body, to_addrs=None,
                          headers=None):
    """Sends a bug notification.

    :bug: The bug the notification concerns.
    :user: The user that did that action that caused a notification to
           be sent.
    :subject: The subject of the notification.
    :body: The body of the notification.
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

    for to_addr in to_addrs:
        simple_sendmail_from_person(
            person=user, to_addrs=to_addr, subject=subject, body=body,
            headers=headers)

def send_bug_edit_notification(bug_delta):
    """Send a notification email about a bug that was modified.

    :bug_delta: has to provide IBugDelta.
    """
    if not IBugDelta.providedBy(bug_delta):
        raise TypeError(
            "Expected an object providing IBugDelta, got %s instead" %
            repr(bug_delta))

    subject, body = generate_bug_edit_email(bug_delta)
    send_bug_notification(bug_delta.bug, bug_delta.user, subject, body)


def send_bug_duplicate_notification(duplicate_bug, user):
    """Send a notification that a bug was marked a dup of a bug.

    The email is sent the duplicate_bug.duplicateOf's subscribers
    telling them which bug ID has been marked as a dup of their bug.
    duplicate_bug is an IBug whose .duplicateof is not
    None.
    """
    bug = duplicate_bug.duplicateof
    if bug is None:
        return
    subject = u"[Bug %d] %s" % (bug.id, bug.title)

    body = u"""\
%(bugurl)s

*** Bug %(duplicate_id)d has been marked a duplicate of this bug ***""" % {
        'duplicate_id' : duplicate_bug.id,
        'bugurl' : canonical_url(bug)}

    send_bug_notification(bug, user, subject, body)

def get_cc_list(bug):
    """Return the list of people that are CC'd on this bug.

    Appends people CC'd on the dup target as well, if this bug is a
    duplicate.
    """
    subscriptions = []
    if not bug.private:
        subscriptions = list(GLOBAL_NOTIFICATION_EMAIL_ADDRS)

    subscriptions += bug.notificationRecipientAddresses()

    return subscriptions


# XXX: Brad Bollenbach, 2005-04-11: This function will probably be
# supplanted by get_bug_delta and get_task_delta (see slightly further
# down.)
def get_changes(before, after, fields):
    """Return what changed from the object before to after for the
    passed-in fields. fields is a tuple of (field_name, display_value_func)
    tuples, where display_value_func is used to convert the differences
    in attribute values into something you could display in, for example,
    a change notification email."""
    changes = {}

    for field_name, display_value_func in fields:
        old_val = getattr(before, field_name, None)
        new_val = getattr(after, field_name, None)
        if old_val != new_val:
            changes[field_name] = {}
            if display_value_func:
                changes[field_name]['old'] = display_value_func(old_val)
                changes[field_name]['new'] = display_value_func(new_val)
            else:
                changes[field_name]['old'] = old_val
                changes[field_name]['new'] = new_val

    return changes


def get_bug_delta(old_bug, new_bug, user):
    """Compute the delta from old_bug to new_bug.

    old_bug and new_bug are IBug's. user is an IPerson. Returns an
    IBugDelta if there are changes, or None if there were no changes.
    """
    changes = {}
    for field_name in ("title", "description"):
        # fields for which we simply show the new value when they
        # change
        old_val = getattr(old_bug, field_name)
        new_val = getattr(new_bug, field_name)
        if old_val != new_val:
            changes[field_name] = new_val

    for field_name in ("name", "private", "duplicateof"):
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
    if (IUpstreamBugTask.providedBy(old_task) and
        IUpstreamBugTask.providedBy(new_task)):
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
        if old_task.binarypackagename != new_task.binarypackagename:
            changes["binarypackagename"] = {}
            changes["binarypackagename"]["old"] = old_task.binarypackagename
            changes["binarypackagename"]["new"] = new_task.binarypackagename
    else:
        raise TypeError(
            "Can't calculate delta on bug tasks of incompatible types: "
            "[%s, %s]" % (repr(old_task), repr(new_task)))

    # calculate the differences in the fields that both types of tasks
    # have in common
    for field_name in ("status", "severity", "priority",
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

    subject, body = generate_bug_add_email(bug)

    send_bug_notification(
        bug, event.user, subject, body,
        headers={'Message-Id': bug.initial_message.rfc822msgid})


def notify_bug_modified(modified_bug, event):
    """Notify the Cc'd list that this bug has been modified.

    modified_bug bug must be an IBug. event must be an
    ISQLObjectModifiedEvent.
    """
    bug_delta = get_bug_delta(
        old_bug=event.object_before_modification,
        new_bug=event.object, user=event.user)

    assert bug_delta is not None

    send_bug_edit_notification(bug_delta)

    if bug_delta.duplicateof is not None:
        # This bug was marked as a duplicate, so notify the dup
        # target subscribers of this as well.
        send_bug_duplicate_notification(
            duplicate_bug=bug_delta.bug,
            user=event.user)


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

    subject, body = generate_bug_edit_email(bug_delta)

    send_bug_notification(bugtask.bug, event.user, subject, body)


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
        user=event.user,
        comment_on_change=event.comment_on_change)

    send_bug_edit_notification(bug_delta)

    update_bug_contact_subscriptions(modified_bugtask, event)


def notify_bug_comment_added(bugmessage, event):
    """Notify CC'd list that a message was added to this bug.

    bugmessage must be an IBugMessage. event must be an
    ISQLObjectCreatedEvent. If bugmessage.bug is a duplicate the
    comment will also be sent to the dup target's subscribers.
    """
    bug = bugmessage.bug
    to_addrs = get_cc_list(bug)

    if ((bug.duplicateof is not None) and (not bug.private)):
        # This bug is a duplicate of another bug, so include the dup
        # target's subscribers in the recipient list, for comments
        # only.
        #
        # NOTE: if the dup is private, the dup target will not receive
        # notifications from the dup.
        #
        # Even though this use case seems highly contrived, I'd rather
        # be paranoid and not reveal anything unexpectedly about a
        # private bug.
        #
        # -- Brad Bollenbach, 2005-04-19
        duplicate_target_emails = \
            bug.duplicateof.notificationRecipientAddresses()
        # Merge the duplicate's notification recipient addresses with
        # those belonging to the dup target.
        to_addrs = list(sets.Set(to_addrs + duplicate_target_emails))
        to_addrs.sort()

    msg = ""

    if bug.duplicateof is not None:
        msg += u"*** This bug is a duplicate of %d ***\n\n" % (
            bug.duplicateof.id)

    subject, body = generate_bug_comment_email(bugmessage)
    msg += body

    message = bugmessage.message
    headers = {'Message-Id': message.rfc822msgid}

    references = []
    reference = message.parent
    while reference is not None:
        references.insert(0, reference.rfc822msgid)
        reference = reference.parent

    headers['References'] = ' '.join(references)
    send_bug_notification(
        bug, event.user, subject, body,
        to_addrs=to_addrs, headers=headers)


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

    send_bug_edit_notification(bug_delta)


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

        send_bug_edit_notification(bug_delta)


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

    send_bug_edit_notification(bug_delta)


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

        send_bug_edit_notification(bug_delta)


def notify_bug_cve_added(bugcve, event):
    """Notify CC'd list that a new cve ref has been added to this bug.

    bugcve must be an IBugCve. event must be an ISQLObjectCreatedEvent.
    """
    bug_delta = BugDelta(
        bug=bugcve.bug,
        bugurl=canonical_url(bugcve.bug),
        user=event.user,
        cve={'new': bugcve.cve})

    send_bug_edit_notification(bug_delta)

def notify_bug_cve_deleted(bugcve, event):
    """Notify CC'd list that a cve ref has been removed from this bug.

    bugcve must be an IBugCve. event must be an ISQLObjectDeletedEvent.
    """
    bug_delta = BugDelta(
        bug=bugcve.bug,
        bugurl=canonical_url(bugcve.bug),
        user=event.user,
        cve={'old': bugcve.cve})

    send_bug_edit_notification(bug_delta)


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

    send_bug_edit_notification(bug_delta)


def notify_join_request(event):
    """Notify team administrators that a new membership is pending approval."""
    if not event.user in event.team.proposedmembers:
        return

    user = event.user
    team = event.team
    to_addrs = sets.Set()
    for person in itertools.chain(team.administrators, [team.teamowner]):
        to_addrs.update(contactEmailAddresses(person))

    if to_addrs:
        url = '%s/+member/%s' % (canonical_url(team), user.name)
        replacements = {'browsername': user.browsername,
                        'name': user.name,
                        'teamname': team.browsername,
                        'url': url}
        template = get_email_template('pending-membership-approval.txt')
        msg = template % replacements
        fromaddress = "Launchpad <noreply@ubuntu.com>"
        subject = "Launchpad: New member awaiting approval."
        simple_sendmail(fromaddress, to_addrs, subject, msg)


def send_ticket_notification(ticket_event, subject, body):
    """Sends a ticket notification to the ticket's subscribers."""
    ticket = ticket_event.object

    sent_addrs = set()
    subscribers = [subscription.person
                   for subscription in ticket.subscriptions]
    for notified_person in subscribers:
        for address in contactEmailAddresses(notified_person):
            if address not in sent_addrs:
                from_address = format_address(
                    ticket_event.user.displayname,
                    'ticket%s@%s' % (
                        ticket_event.object.id,
                        config.tickettracker.email_domain))
                simple_sendmail(
                    from_address, address, subject, body)
                sent_addrs.add(address)


def notify_ticket_added(ticket, event):
    """Notify the subscribers of the newly added ticket."""
    subject = '[Support #%s]: %s' % (ticket.id, ticket.title)
    body = get_email_template('ticket_added.txt') % {
        'target_name': ticket.target.displayname,
        'ticket_id': ticket.id,
        'ticket_url': canonical_url(ticket),
        'comment': ticket.description}

    send_ticket_notification(event, subject, body)


def get_ticket_changes_text(ticket, old_ticket):
    """Return a textual representation of the changes."""
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
        info_fields.append('Description changed to:\n%s' % ticket.description)

    ticket_changes = '\n\n'.join(info_fields)
    return ticket_changes


def notify_ticket_modified(ticket, event):
    """Notify the subscribers that a ticket has been modifed."""
    old_ticket = event.object_before_modification

    body = get_ticket_changes_text(ticket, old_ticket)

    new_comments = set(ticket.messages).difference(old_ticket.messages)
    nr_of_new_comments = len(new_comments)
    if len(new_comments) == 0:
        comment_subject = ticket.title
    elif len(new_comments) == 1:
        comment = new_comments.pop()
        comment_subject = comment.subject
        if body:
            # There should be a blank line between the changes and the
            # comment.
            body += '\n\n'
        body += 'Comment:\n%s' % comment.text_contents
    else:
        raise AssertionError(
            "There shouldn't be more than one comment for a notification.")

    if not body:
        # No interesting changes were made.
        return

    subject = '[Support #%s]: %s' % (ticket.id, comment_subject)


    body = get_email_template('ticket_modified.txt') % {
        'ticket_id': ticket.id,
        'target_name': ticket.target.displayname,
        'ticket_url': canonical_url(ticket),
        'body': body}
    send_ticket_notification(event, subject, body)


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

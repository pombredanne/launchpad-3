# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Event handlers that send email notifications."""

__metaclass__ = type

import os.path
import itertools
import sets
import textwrap

from zope.security.proxy import isinstance as zope_isinstance

import canonical.launchpad
from canonical.config import config
from canonical.launchpad.interfaces import (
    IBugDelta, IUpstreamBugTask, IDistroBugTask, IDistroReleaseBugTask)
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.components.bug import BugDelta
from canonical.launchpad.components.bugtask import BugTaskDelta
from canonical.launchpad.helpers import contactEmailAddresses
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


def get_email_template(filename):
    """Returns the email template with the given file name.

    The templates are located in 'lib/canonical/launchpad/emailtemplates'.
    """
    base = os.path.dirname(canonical.launchpad.__file__)
    fullpath = os.path.join(base, 'emailtemplates', filename)
    return open(fullpath).read()


def get_bugmail_from_address(user):
    """Return an appropriate bugmail From address.

    :user: an IPerson whose name will appear in the From address, e.g.:

        From: Foo Bar <foo.bar@canonical.com>
    """
    return u"%s <%s>" % (user.displayname, user.preferredemail.email)


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


def send_process_error_notification(to_addrs, subject, error_msg):
    """Sends an error message.

    Tells the user that an error was encountered while processing
    his request.
    """
    msg = get_email_template('email-processing-error.txt') % {
            'error_msg': error_msg}
    simple_sendmail(get_bugmail_error_address(), to_addrs, subject, msg)


def notify_errors_list(message, file_alias):
    """Sends an error to the Launchpad errors list."""
    template = get_email_template('notify-unhandled-email.txt')
    simple_sendmail(
        get_bugmail_error_address(), [config.launchpad.errors_address],
        'Unhandled Email: %s' % file_alias.filename,
        template % {'url': file_alias.url, 'error_msg': message})


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
    #
    # XXX, Brad Bollenbach, 2005-06-29: A hack to workaround some data
    # migration issues; many older bugs don't have descriptions
    # set. The bug filed for this is at:
    #
    # https://launchpad.ubuntu.com/malone/bugs/1187
    if bug.description:
        description = bug.description
    else:
        # This bug is in need of some data migration love.
        description = bug.messages[0].contents

    body += u"\n"
    mailwrapper = MailWrapper(width=72)
    body += u"Description:\n%s" % mailwrapper.format(description)

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
        body += u"Title changed to:\n"
        body += u"    %s\n" % bug_delta.title

    if bug_delta.summary is not None:
        body += u"Summary changed to:\n"
        body += mailwrapper.format(bug_delta.summary)
        body += u"\n"

    if bug_delta.description is not None:
        body += u"Description changed to:\n"
        body += mailwrapper.format(bug_delta.description)
        body += u"\n"

    if bug_delta.private is not None:
        body += u"Secrecy changed to:\n"
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

            if bugtask_delta.statusexplanation is not None:
                status_exp_line = u"%15s: %s" % (
                    u"Explanation", bugtask_delta.statusexplanation)
                status_exp_wrapper = MailWrapper(
                    width=72, indent=u" " * 17, indent_first_line=False)
                body += status_exp_wrapper.format(status_exp_line)
                body += u"\n"

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
            body += u"Also affects: %s" % added_bugtask.targetname
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
                    bug_comment.message.contents)})

    return (subject, body)


def send_bug_notification(bug, user, subject, body,
                          to_addrs=None, headers=None):
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

    if headers is None:
        headers = {}
    if to_addrs is None:
        to_addrs = get_cc_list(bug)

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
    if "Sender" not in headers:
        headers["Sender"] = config.bounce_address
    from_addr = get_bugmail_from_address(user)
    for to_addr in to_addrs:
        simple_sendmail(from_addr, to_addr, subject, body, headers=headers)


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
    for field_name in ("title", "summary", "description"):
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

    if old_task.statusexplanation != new_task.statusexplanation:
        changes["statusexplanation"] = new_task.statusexplanation

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
        user=event.user)

    send_bug_edit_notification(bug_delta)


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
        url = "%s/people/%s/+members/%s" % (event.appurl, team.name, user.name)
        replacements = {'browsername': user.browsername,
                        'name': user.name,
                        'teamname': team.browsername,
                        'url': url}
        template = get_email_template('pending-membership-approval.txt')
        msg = template % replacements
        fromaddress = "Launchpad <noreply@ubuntu.com>"
        subject = "Launchpad: New member awaiting approval."
        simple_sendmail(fromaddress, to_addrs, subject, msg)

# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Handle incoming Bugs email."""

__metaclass__ = type
__all__ = [
    "MaloneHandler",
    ]

import os

from lazr.lifecycle.event import ObjectCreatedEvent
from lazr.lifecycle.interfaces import IObjectCreatedEvent
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from canonical.database.sqlbase import rollback
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mailnotification import (
    MailWrapper,
    send_process_error_notification,
    )
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.bugs.interfaces.bug import CreatedBugWithNoBugTasksError
from lp.bugs.interfaces.bugattachment import (
    BugAttachmentType,
    IBugAttachmentSet,
    )
from lp.bugs.interfaces.bugmessage import IBugMessageSet
from lp.bugs.mail.commands import BugEmailCommands
from lp.services.mail.helpers import (
    ensure_not_weakly_authenticated,
    get_error_message,
    get_main_body,
    guess_bugtask,
    IncomingEmailError,
    parse_commands,
    reformat_wiki_text,
    )
from lp.services.mail.interfaces import (
    EmailProcessingError,
    IBugEditEmailCommand,
    IBugEmailCommand,
    IBugTaskEditEmailCommand,
    IBugTaskEmailCommand,
    IMailHandler,
    )
from lp.services.mail.sendmail import simple_sendmail
from lp.services.messages.interfaces.message import IMessageSet


error_templates = os.path.join(os.path.dirname(__file__), 'errortemplates')


class MaloneHandler:
    """Handles emails sent to Malone.

    It only handles mail sent to new@... and $bugid@..., where $bugid is a
    positive integer.
    """
    implements(IMailHandler)

    allow_unknown_users = False

    def getCommands(self, signed_msg):
        """Returns a list of all the commands found in the email."""
        content = get_main_body(signed_msg)
        if content is None:
            return []
        return [BugEmailCommands.get(name=name, string_args=args) for
                name, args in parse_commands(content,
                                             BugEmailCommands.names())]

    def extractAndAuthenticateCommands(self, signed_msg, to_addr):
        """Extract commands and handle special destinations.

        NB: The authentication is carried out against the current principal,
        not directly against the message.  authenticateEmail must previously
        have been called on this thread.

        :returns: (final_result, add_comment_to_bug, commands)
            If final_result is non-none, stop processing and return this value
            to indicate whether the message was dealt with or not.
            If add_comment_to_bug, add the contents to the first bug
            selected.
            commands is a list of bug commands.
        """
        CONTEXT = 'bug report'
        commands = self.getCommands(signed_msg)
        to_user, to_host = to_addr.split('@')
        add_comment_to_bug = False
        # If there are any commands, we must have strong authentication.
        # We send a different failure message for attempts to create a new
        # bug.
        if to_user.lower() == 'new':
            ensure_not_weakly_authenticated(signed_msg, CONTEXT,
                'unauthenticated-bug-creation.txt',
                error_templates=error_templates)
        elif len(commands) > 0:
            ensure_not_weakly_authenticated(signed_msg, CONTEXT)
        if to_user.lower() == 'new':
            commands.insert(0, BugEmailCommands.get('bug', ['new']))
        elif to_user.isdigit():
            # A comment to a bug. We set add_comment_to_bug to True so
            # that the comment gets added to the bug later. We don't add
            # the comment now, since we want to let the 'bug' command
            # handle the possible errors that can occur while getting
            # the bug.
            add_comment_to_bug = True
            commands.insert(0, BugEmailCommands.get('bug', [to_user]))
        elif to_user.lower() == 'help':
            from_user = getUtility(ILaunchBag).user
            if from_user is not None:
                preferredemail = from_user.preferredemail
                if preferredemail is not None:
                    to_address = str(preferredemail.email)
                    self.sendHelpEmail(to_address)
            return True, False, None
        elif to_user.lower() != 'edit':
            # Indicate that we didn't handle the mail.
            return False, False, None
        return None, add_comment_to_bug, commands

    def process(self, signed_msg, to_addr, filealias=None, log=None):
        """See IMailHandler."""

        try:
            (final_result, add_comment_to_bug,
                commands, ) = self.extractAndAuthenticateCommands(
                    signed_msg, to_addr)
            if final_result is not None:
                return final_result

            bug = None
            bug_event = None
            bugtask = None
            bugtask_event = None

            processing_errors = []
            while len(commands) > 0:
                command = commands.pop(0)
                try:
                    if IBugEmailCommand.providedBy(command):
                        if bug_event is not None:
                            try:
                                notify(bug_event)
                            except CreatedBugWithNoBugTasksError:
                                rollback()
                                raise IncomingEmailError(
                                    get_error_message(
                                        'no-affects-target-on-submit.txt',
                                        error_templates=error_templates))
                        if (bugtask_event is not None and
                            not IObjectCreatedEvent.providedBy(bug_event)):
                            notify(bugtask_event)
                        bugtask = None
                        bugtask_event = None

                        bug, bug_event = command.execute(
                            signed_msg, filealias)
                        if add_comment_to_bug:
                            messageset = getUtility(IMessageSet)
                            message = messageset.fromEmail(
                                signed_msg.as_string(),
                                owner=getUtility(ILaunchBag).user,
                                filealias=filealias,
                                parsed_message=signed_msg,
                                fallback_parent=bug.initial_message)

                            # If the new message's parent is linked to
                            # a bug watch we also link this message to
                            # that bug watch.
                            bug_message_set = getUtility(IBugMessageSet)
                            parent_bug_message = (
                                bug_message_set.getByBugAndMessage(
                                    bug, message.parent))

                            if (parent_bug_message is not None and
                                parent_bug_message.bugwatch):
                                bug_watch = parent_bug_message.bugwatch
                            else:
                                bug_watch = None

                            bugmessage = bug.linkMessage(
                                message, bug_watch)

                            notify(ObjectCreatedEvent(bugmessage))
                            add_comment_to_bug = False
                        else:
                            message = bug.initial_message
                        self.processAttachments(bug, message, signed_msg)
                    elif IBugTaskEmailCommand.providedBy(command):
                        if bugtask_event is not None:
                            if not IObjectCreatedEvent.providedBy(bug_event):
                                notify(bugtask_event)
                            bugtask_event = None
                        bugtask, bugtask_event = command.execute(bug)
                    elif IBugEditEmailCommand.providedBy(command):
                        bug, bug_event = command.execute(bug, bug_event)
                    elif IBugTaskEditEmailCommand.providedBy(command):
                        if bugtask is None:
                            if len(bug.bugtasks) == 0:
                                rollback()
                                raise IncomingEmailError(
                                    get_error_message(
                                        'no-affects-target-on-submit.txt',
                                        error_templates=error_templates))
                            bugtask = guess_bugtask(
                                bug, getUtility(ILaunchBag).user)
                            if bugtask is None:
                                raise IncomingEmailError(get_error_message(
                                    'no-default-affects.txt',
                                    error_templates=error_templates,
                                    bug_id=bug.id,
                                    nr_of_bugtasks=len(bug.bugtasks)))
                        bugtask, bugtask_event = command.execute(
                            bugtask, bugtask_event)

                except EmailProcessingError, error:
                    processing_errors.append((error, command))
                    if error.stop_processing:
                        commands = []
                        rollback()
                    else:
                        continue

            if len(processing_errors) > 0:
                raise IncomingEmailError(
                    '\n'.join(str(error) for error, command
                              in processing_errors),
                    [command for error, command in processing_errors])

            if bug_event is not None:
                try:
                    notify(bug_event)
                except CreatedBugWithNoBugTasksError:
                    rollback()
                    raise IncomingEmailError(
                        get_error_message(
                            'no-affects-target-on-submit.txt',
                            error_templates=error_templates))
            if bugtask_event is not None:
                if not IObjectCreatedEvent.providedBy(bug_event):
                    notify(bugtask_event)

        except IncomingEmailError, error:
            send_process_error_notification(
                str(getUtility(ILaunchBag).user.preferredemail.email),
                'Submit Request Failure',
                error.message, signed_msg, error.failing_command)

        return True

    def sendHelpEmail(self, to_address):
        """Send usage help to `to_address`."""
        # Get the help text (formatted as MoinMoin markup)
        help_text = get_email_template('help.txt')
        help_text = reformat_wiki_text(help_text)
        # Wrap text
        mailwrapper = MailWrapper(width=72)
        help_text = mailwrapper.format(help_text)
        simple_sendmail(
            'help@bugs.launchpad.net', to_address,
            'Launchpad Bug Tracker Email Interface Help',
            help_text)

    # Some content types indicate that an attachment has a special
    # purpose. The current set is based on parsing emails from
    # one mail account and may need to be extended.
    #
    # Mail signatures are most likely generated by the mail client
    # and hence contain not data that is interesting except for
    # mail authentication.
    #
    # Resource forks of MacOS files are not easily represented outside
    # MacOS; if a resource fork contains useful debugging information,
    # the entire MacOS file should be sent encapsulated for example in
    # MacBinary format.
    #
    # application/ms-tnef attachment are created by Outlook; they
    # seem to store no more than an RTF representation of an email.

    irrelevant_content_types = set((
        'application/applefile',  # the resource fork of a MacOS file
        'application/pgp-signature',
        'application/pkcs7-signature',
        'application/x-pkcs7-signature',
        'text/x-vcard',
        'application/ms-tnef',
        ))

    def processAttachments(self, bug, message, signed_mail):
        """Create Bugattachments for "reasonable" mail attachments.

        A mail attachment is stored as a bugattachment if its
        content type is not listed in irrelevant_content_types.
        """
        for chunk in message.chunks:
            blob = chunk.blob
            if blob is None:
                continue
            # Mutt (other mail clients too?) appends the filename to the
            # content type.
            content_type = blob.mimetype.split(';', 1)[0]
            if content_type in self.irrelevant_content_types:
                continue

            if content_type == 'text/html' and blob.filename == 'unnamed':
                # This is the HTML representation of the main part of
                # an email.
                continue

            if content_type in ('text/x-diff', 'text/x-patch'):
                attach_type = BugAttachmentType.PATCH
            else:
                attach_type = BugAttachmentType.UNSPECIFIED

            getUtility(IBugAttachmentSet).create(
                bug=bug, filealias=blob, attach_type=attach_type,
                title=blob.filename, message=message, send_notifications=True)

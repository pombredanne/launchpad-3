# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import transaction
from zope.component import getUtility
from zope.interface import implements
from zope.event import notify
from zope.exceptions import NotFoundError

from canonical.launchpad.helpers import Snapshot, is_maintainer
from canonical.launchpad.interfaces import (
    ILaunchBag, IMessageSet, IBugEmailCommand, IBugTaskEmailCommand,
    IBugEditEmailCommand, IBugTaskEditEmailCommand, IBug, IBugTask,
    IMailHandler, IBugMessageSet, BugCreationConstraintsError,
    EmailProcessingError, IUpstreamBugTask, IDistroBugTask,
    IDistroReleaseBugTask)
from canonical.launchpad.mail.commands import emailcommands
from canonical.launchpad.mailnotification import (
    send_process_error_notification)

from canonical.launchpad.event import (
    SQLObjectModifiedEvent, SQLObjectCreatedEvent)
from canonical.launchpad.event.interfaces import (
    ISQLObjectModifiedEvent, ISQLObjectCreatedEvent)


def get_main_body(signed_msg):
    """Returns the first text part of the email."""
    msg = signed_msg.signedMessage
    if msg is None:
        # The email wasn't signed.
        return None
    if msg.is_multipart():
        for part in msg.get_payload():
            if part.get_content_type() == 'text/plain':
                return part.get_payload(decode=True)
    else:
        return msg.get_payload(decode=True)


def get_edited_fields(modified_event, another_event):
    """Combines two events' edited_fields."""
    edited_fields = modified_event.edited_fields
    if ISQLObjectModifiedEvent.providedBy(another_event):
        edited_fields += another_event.edited_fields
    return edited_fields


def get_bugtask_type(bugtask):
    """Returns the specific IBugTask interface the the bugtask provides.

        >>> from canonical.launchpad.interfaces import (
        ...     IUpstreamBugTask, IDistroBugTask, IDistroReleaseBugTask)
        >>> from zope.interface import classImplementsOnly
        >>> class BugTask:
        ...     pass

        >>> classImplementsOnly(BugTask, IUpstreamBugTask)
        >>> get_bugtask_type(BugTask()) #doctest: +ELLIPSIS
        <...IUpstreamBugTask>

        >>> classImplementsOnly(BugTask, IDistroBugTask)
        >>> get_bugtask_type(BugTask()) #doctest: +ELLIPSIS
        <...IDistroBugTask>

        >>> classImplementsOnly(BugTask, IDistroReleaseBugTask)
        >>> get_bugtask_type(BugTask()) #doctest: +ELLIPSIS
        <...IDistroReleaseBugTask>
    """
    bugtask_interfaces = [
        IUpstreamBugTask, IDistroBugTask, IDistroReleaseBugTask
        ]
    for interface in bugtask_interfaces:
        if interface.providedBy(bugtask):
            return interface
    # The bugtask didn't provide any specific interface.
    raise TypeError(
        'No specific bugtask interface was provided by %r' % bugtask)


def guess_bugtask(bug, person):
    """Guess which bug task the person intended to edit.

    Return None if no bug task could be guessed.
    """
    if len(bug.bugtasks) == 1:
        return bug.bugtasks[0]
    else:
        for bugtask in bug.bugtasks:
            if bugtask.product and is_maintainer(bugtask.product, person):
                return bugtask
            elif (bugtask.distribution and
                  person.inTeam(bugtask.distribution.members)):
                return bugtask
            elif (bugtask.sourcepackagename and
                  person.inTeam(bugtask.maintainer)):
                return bugtask

    return None


class IncomingEmailError(Exception):
    """Indicates that something went wrong processing the mail."""
    def __init__(self, message):
        self.message = message


class MaloneHandler:
    """Handles emails sent to Malone.

    It only handles mail sent to new@... and $bugid@..., where $bugid is a
    positive integer.
    """
    implements(IMailHandler)

    def getCommands(self, signed_msg):
        """Returns a list of all the commands found in the email."""
        commands = []
        content = get_main_body(signed_msg)
        if content is None:
            # The email wasn't signed, don't process any commands.
            #XXX: We should provide an error message if the user tries to
            #     give commands in an unsigned email.
            #     -- Bjorn Tillenius, 2005-06-06
            return []
        # First extract all commands from the email.   
        command_names = emailcommands.names()
        for line in content.splitlines():  
            # All commands have to be indented.
            if line.startswith(' ') or line.startswith('\t'):
                command_string = line.strip()
                words = command_string.split(' ')
                if words and words[0] in command_names:
                    command = emailcommands.get(
                        name=words[0], string_args=words[1:])
                    if commands and commands[-1].isSubCommand(command): 
                        commands[-1].addSubCommandToBeExecuted(command)
                    else:
                        commands.append(command)
        return commands


    def process(self, signed_msg, to_addr, filealias=None):
        commands = self.getCommands(signed_msg)

        user, host = to_addr.split('@')

        add_comment_to_bug = False
        if user.lower() == 'new':
            # A submit request.   
            commands.insert(0, emailcommands.get('bug', ['new']))
        elif user.isdigit():
            # A comment to a bug. We set add_comment_to_bug to True so
            # that the comment gets added to the bug later. We don't add
            # the comment now, since we want to let the 'bug' command
            # handle the possible errors that can occur while getting
            # the bug.
            add_comment_to_bug = True
            commands.insert(0, emailcommands.get('bug', [user]))
        elif user.lower() != 'edit':
            # Indicate that we didn't handle the mail.
            return False

        bug = None
        bug_event = None
        bugtask = None
        bugtask_event = None
        bugtask_snapshot = None
        try:
            while len(commands) > 0:
                command = commands.pop(0)
                try:
                    if IBugEmailCommand.providedBy(command):
                        if bug_event is not None:
                            notify(bug_event)
                            bug_event = None

                        bug, bug_event = command.execute(signed_msg, filealias)
                        if add_comment_to_bug:
                            messageset = getUtility(IMessageSet)
                            message = messageset.fromEmail(
                                signed_msg.as_string(),
                                owner=getUtility(ILaunchBag).user,
                                filealias=filealias,
                                parsed_message=signed_msg,
                                fallback_parent=bug.initial_message)
                            bugmessage = bug.linkMessage(message)
                            notify(SQLObjectCreatedEvent(bugmessage))
                            add_comment_to_bug = False
                        bug_snapshot = Snapshot(bug, providing=IBug)
                    elif IBugTaskEmailCommand.providedBy(command):
                        if bugtask_event is not None:
                            notify(bugtask_event)
                            bugtask_event = None
                            bugtask_snapshot = None
                        bugtask, bugtask_event = command.execute(bug)
                        if (bugtask_snapshot is None and
                            ISQLObjectModifiedEvent.providedBy(bugtask_event)):
                            bugtask_snapshot = (
                                bugtask_event.object_before_modification)
                        elif bugtask_snapshot is None:
                            bugtask_snapshot = Snapshot(
                                bugtask, providing=IBugTask)
                    elif IBugEditEmailCommand.providedBy(command):
                        ob, ob_event = command.execute(bug, bug_event)
                        # The bug can be edited by several commands. Let's wait
                        # firing off the event until all commands related to
                        # the bug have been executed.
                        if ob_event is not None:
                            if ob != bug:
                                notify(ob_event)
                            elif ISQLObjectModifiedEvent.providedBy(ob_event):
                                edited_fields = get_edited_fields(
                                    ob_event, bug_event)
                                bug_event = SQLObjectModifiedEvent(
                                    bug, bug_snapshot, edited_fields)
                    elif IBugTaskEditEmailCommand.providedBy(command):
                        if bugtask is None:
                            bugtask = guess_bugtask(
                                bug, getUtility(ILaunchBag).user)
                            bugtask_snapshot = Snapshot(
                                bugtask, providing=get_bugtask_type(bugtask))
                        ob, ob_event = command.execute(bugtask, bugtask_event)
                        # The bug task can be edited by several
                        # commands. Let's wait firing off the event
                        # until all commands related to the bug task
                        # have been executed.
                        if ob_event is not None:
                            if ob != bugtask:
                                notify(ob_event)
                            elif ISQLObjectModifiedEvent.providedBy(ob_event):
                                edited_fields = get_edited_fields(
                                    ob_event, bugtask_event)
                                bugtask_event = SQLObjectModifiedEvent(
                                    bugtask, bugtask_snapshot, edited_fields)

                except EmailProcessingError, error:
                    raise IncomingEmailError(str(error))

            if bug_event is not None:
                try:
                    notify(bug_event)
                except BugCreationConstraintsError, error:
                    raise IncomingEmailError(str(error))
            if bugtask_event is not None:
                notify(bugtask_event)

        except IncomingEmailError, error:
            transaction.abort()
            send_process_error_notification(
                signed_msg['From'],
                'Submit Request Failure',
                error.message)

        return True

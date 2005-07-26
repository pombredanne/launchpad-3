# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import email

import transaction
from zope.component import getUtility
from zope.interface import Interface, implements
from zope.event import notify
from zope.exceptions import NotFoundError
from zope.publisher.interfaces.browser import IBrowserRequest

from canonical.config import config
from canonical.launchpad.helpers import Snapshot
from canonical.launchpad.interfaces import (
    ILaunchBag, IBugSet, IBugTask, IProduct, IDistribution, IMessageSet,
    IBugEmailCommand, IBugTaskSet, IBug, IMailHandler,
    BugCreationConstraintsError)
from canonical.launchpad.mail.commands import emailcommands
from canonical.launchpad.mailnotification import (
    send_process_error_notification)

from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.event.interfaces import ISQLObjectModifiedEvent


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
        edited_fields.append(another_event.edited_fields)
    return edited_fields


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

    def getMessage(self, parsed_msg, filealias):
        messageset = getUtility(IMessageSet)
        try:
            message = messageset.get(parsed_msg['Message-Id'])
        except NotFoundError:
            message = messageset.fromEmail(
                parsed_msg.as_string(),
                owner=getUtility(ILaunchBag).user,
                filealias=filealias,
                parsed_message=parsed_msg)
        return message

    def getCommands(self, signed_msg):
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
            # All commands have to be intented.
            if line.startswith(' ') or line.startswith('\t'):
                words = line.split()
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
        
        if user.lower() == 'new':
            # A submit request.   
            commands.insert(0, emailcommands.get('bug', ['new']))
        elif user.isdigit():
            # A comment to a bug.
            commands.insert(0, emailcommands.get('bug', [user]))
        else:
            # Indicate that we didn't handle the mail.
            return False

        message = self.getMessage(signed_msg, filealias)

        bug = None
        bug_event = None
        try:
            while len(commands) > 0:    
                command = commands.pop(0)
                try:
                    if IBugEmailCommand.providedBy(command):   
                        if bug_event is not None:
                            notify(bug_event)
                            bug_event = None

                        bug, bug_event = command.execute(message)
                        bug_snapshot = Snapshot(bug, providing=IBug)
                    else:
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
                except ValueError, error:
                    raise IncomingEmailError(str(error))

            if bug_event is not None:
                try:
                    notify(bug_event)
                except BugCreationConstraintsError, error:
                    raise IncomingEmailError(str(error))

        except IncomingEmailError, error:
            transaction.abort()
            send_process_error_notification(
                signed_msg['From'],
                'Submit Request Failure',
                error.message)
                
        return True

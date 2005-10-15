# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Interfaces specific to mail handling."""

__metaclass__ = type
__all__ = ['ISignedMessage',
           'IMailHandler',
           'IEmailCommand',
           'IBugEmailCommand',
           'IBugEditEmailCommand']

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute
from zope.schema import ASCII

class ISignedMessage(Interface):
    """A message that's possibly signed with a GPG key.

    If the message wasn't signed, all attributes will be None.
    """

    def __getitem__(name):
        """Returns the message header with the given name."""

    signedMessage = Attribute("The part that was signed, represented "
                              "as an email.Message.")

    signedContent = ASCII(title=_("Signed Content"),
                          description=_("The text that was signed."))

    signature = ASCII(title=_("Signature"),
                      description=_("The GPG signature used to sign "
                                    "the email"))


class IMailHandler(Interface):
    """Handles incoming mail sent to a specific email domain.

    For example, in email address '1@bugs.launchpad.ubuntu.com',
    'bugs.launchpad.ubuntu.com' is the email domain.

    The handler should be registered as a named utility, with the domain
    it handles as the name.
    """

    def process(signed_msg, to_address, filealias):
        """Processes a ISignedMessage

        The 'to_address' is the address the mail was sent to.
        The 'filealias' is an ILibraryFileAlias.

        Return True if the mesage was processed, otherwise False.
        """


class IEmailCommand(Interface):
    """An email command.

    Email commands can be embedded in mails sent to Launchpad. For
    example in comments to bugs sent via email, you can include:

      private yes

    in order to make the bug private.
    """
    subCommands = Attribute("A list of subcommand names.")

    def execute(context):
        """Execute the command in a context."""

    def isSubCommand(command):
        """Return whether the command is a sub command or not."""

    def addSubCommandToBeExecuted(subcommand):
        """Adds a sub command to be executed when this command is."""


class IBugEmailCommand(IEmailCommand):
    """An email command specific to getting or creating a bug."""

    def execute(parsed_msg, filealias):
        """Either create or get an exiting bug.

        If a bug is created, parsed_msg and filealias will be used to
        create the initial comment of the bug.

        The bug and an event is returned as a two-tuple.
        """


class IBugEditEmailCommand(IEmailCommand):
    """An email command specific to editing bug.

    It edits either the bug directly or a sub object of the bug, like a
    bug task.
    """

    def execute(bug):
        """Execute the command in the context of the bug.

        The modified object and an event is returned.
        """

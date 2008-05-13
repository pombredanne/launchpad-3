# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces specific to mail handling."""

__metaclass__ = type
__all__ = ['IWeaklyAuthenticatedPrincipal',
           'ISignedMessage',
           'IMailHandler',
           'EmailProcessingError',
           'BugTargetNotFound',
           'IEmailCommand',
           'IBugEmailCommand',
           'IBugTaskEmailCommand',
           'IBugEditEmailCommand',
           'IBugTaskEditEmailCommand']

from zope.interface import Interface, Attribute
from zope.schema import ASCII, Bool
from canonical.launchpad import _


class IWeaklyAuthenticatedPrincipal(Interface):
    """The principal has been weakly authenticated.

    At the moment it means that the user was authenticated simply by
    looking at the From address in an email.
    """


class ISignedMessage(Interface):
    """A message that's possibly signed with an OpenPGP key.

    If the message wasn't signed, all attributes will be None.
    """

    def __getitem__(name):
        """Returns the message header with the given name."""

    signedMessage = Attribute("The part that was signed, represented "
                              "as an email.Message.")

    signedContent = ASCII(title=_("Signed Content"),
                          description=_("The text that was signed."))

    signature = ASCII(title=_("Signature"),
                      description=_("The OpenPGP signature used to sign "
                                    "the message."))

    parsed_string = Attribute(
        "The string that was parsed to create the SignedMessage.")


class IMailHandler(Interface):
    """Handles incoming mail sent to a specific email domain.

    For example, in email address '1@bugs.launchpad.ubuntu.com',
    'bugs.launchpad.ubuntu.com' is the email domain.

    The handler should be registered as a named utility, with the domain
    it handles as the name.
    """

    allow_unknown_users = Bool(
        title=u"Allow unknown users",
        description=u"The handler can handle emails from persons not"
                    " registered in Launchpad (which will result in an"
                    " anonymous interaction being set up.")

    def process(signed_msg, to_address, filealias, log=None):
        """Processes a ISignedMessage

        The 'to_address' is the address the mail was sent to.
        The 'filealias' is an ILibraryFileAlias.
        The 'log' is the logger to be used.

        Return True if the mesage was processed, otherwise False.
        """


class EmailProcessingError(Exception):
    """Something went wrong while processing an email command."""

    def __init__(self, args, stop_processing=False):
        """Initialize

        :args: The standard exception extra arguments.
        "stop_processing: Should the processing of the email be stopped?
        """
        Exception.__init__(self, args)
        self.stop_processing = stop_processing


class BugTargetNotFound(Exception):
    """A bug target couldn't be found."""


class IEmailCommand(Interface):
    """An email command.

    Email commands can be embedded in mails sent to Launchpad. For
    example in comments to bugs sent via email, you can include:

      private yes

    in order to make the bug private.
    """

    def execute(context):
        """Execute the command in a context."""

    def setAttributeValue(context, attr_name, attr_value):
        """Set the value of the attribute.

        Subclasses may want to override this if, for example, the
        attribute is set through a special method instead of a normal
        attribute.
        """

    def __str__():
        """Return a textual representation of the command and its arguments.
        """


class IBugEmailCommand(IEmailCommand):
    """An email command specific to getting or creating a bug."""

    def execute(parsed_msg, filealias, commands):
        """Either create or get an exiting bug.

        If a bug is created, parsed_msg and filealias will be used to
        create the initial comment of the bug.

        The remaining commands are examined to make sure we have
        sufficient information for filing a new bug.

        The bug and an event is returned as a two-tuple.
        """


class IBugTaskEmailCommand(IEmailCommand):
    """An email command specific to getting or creating a bug task."""

    def execute(bug):
        """Either create or get an exiting bug task.

        The bug task and an event is returned as a two-tuple.
        """


class IBugEditEmailCommand(IEmailCommand):
    """An email command specific to editing a bug."""

    def execute(bug, current_event):
        """Execute the command in the context of the bug.

        The modified bug and an event is returned.
        """


class IBugTaskEditEmailCommand(IEmailCommand):
    """An email command specific to editing a bug task."""

    def execute(bugtask, current_event):
        """Execute the command in the context of the bug task.

        The modified bug task and an event is returned.
        """

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug message interfaces."""

__metaclass__ = type

__all__ = ['IBugComment', 'IBugMessage', 'IBugMessageSet']

from zope.interface import Attribute, Interface
from zope.schema import Bool, Int, Text

from canonical.launchpad.interfaces.launchpad import IHasBug
from canonical.launchpad.interfaces.message import IMessage


class IBugMessage(IHasBug):
    """A link between a bug and a message."""

    bug = Attribute("The bug.")
    message = Attribute("The message.")


class IBugMessageSet(Interface):
    """The set of all IBugMessages."""

    def createMessage(subject, bug, owner, content=None):
        """Create an IBugMessage.

        title -- a string
        bug -- an IBug
        owner -- an IPerson
        content -- a string

        The created message will have the bug's initial message as its
        parent.

        Returns the created IBugMessage.
        """

    def get(bugmessageid):
        """Retrieve an IBugMessage by its ID."""

    def getByBugAndMessage(bug, message):
        """Return the corresponding IBugMesssage.

        Return None if no such IBugMesssage exists.
        """


class IBugComment(IMessage):
    """A bug comment for displaying in the web UI."""

    bugtask = Attribute(
        """The bug task the comment belongs to.

        Comments are global to bugs, but the bug task is needed in order
        to construct the correct URL.
        """)
    index = Int(title=u'The comment number', required=True)
    is_truncated = Bool(
        title=u'Whether the displayed text is truncated or not.',
        required=True)
    text_for_display = Text(
        title=u'The comment text to be displayed in the UI.')

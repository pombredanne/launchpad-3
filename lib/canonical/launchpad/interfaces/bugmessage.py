# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Bug message interfaces."""

__metaclass__ = type
__all__ = [
    'IBugComment',
    'IBugMessage',
    'IBugMessageAddForm',
    'IBugMessageSet',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Bool, Bytes, Int, Object, Text, TextLine

from canonical.launchpad.fields import Title
from canonical.launchpad.interfaces.bug import IBug
from canonical.launchpad.interfaces.bugwatch import IBugWatch
from canonical.launchpad.interfaces.launchpad import IHasBug
from canonical.launchpad.interfaces.message import IMessage
from canonical.launchpad.validators.bugattachment import (
    bug_attachment_size_constraint)


class IBugMessage(IHasBug):
    """A link between a bug and a message."""

    bug = Object(schema=IBug, title=u"The bug.")
    message = Object(schema=IMessage, title=u"The message.")
    bugwatch = Object(schema=IBugWatch,
        title=u"A bugwatch to which the message pertains.")
    remote_comment_id = TextLine(
        title=u"The id this comment has in the bugwatch's bug tracker.")


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

    def getImportedBugMessages(bug):
        """Return all the imported IBugMesssages for a bug.

        An IBugMesssage is considered imported if it's linked to a bug
        watch.
        """


class IBugMessageAddForm(Interface):
    """Schema used to build the add form for bug comment/attachment."""

    subject = Title(title=u"Subject", required=True)
    comment = Text(title=u"Comment", required=False)
    filecontent = Bytes(
        title=u"Attachment", required=False,
        constraint=bug_attachment_size_constraint)
    patch = Bool(title=u"This attachment is a patch", required=False,
        default=False)
    attachment_description = Title(title=u'Description', required=False)
    email_me = Bool(
        title=u"E-mail me about changes to this bug report",
        required=False, default=False)
    bugwatch_id = Int(
        title=(u"Synchronize this comment with a remote bug "
               "tracker using the bug watch with this id."),
        required=False, default=None)


class IBugComment(IMessage):
    """A bug comment for displaying in the web UI."""

    bugtask = Attribute(
        """The bug task the comment belongs to.

        Comments are global to bugs, but the bug task is needed in order
        to construct the correct URL.
        """)
    bugwatch = Attribute('The bugwatch to which the comment pertains.')
    can_be_shown = Bool(
        title=u'Whether or not the comment can be displayed',
        readonly=True)
    index = Int(title=u'The comment number', required=True, readonly=True)
    was_truncated = Bool(
        title=u'Whether the displayed text was truncated for display.',
        readonly=True)
    text_for_display = Text(
        title=u'The comment text to be displayed in the UI.', readonly=True)
    display_title = Attribute('Whether or not to show the title.')
    synchronized = Attribute(
        'Has the comment been synchronized with a remote bug tracker?')
    add_comment_url = Attribute(
        'The URL for submitting replies to this comment.')

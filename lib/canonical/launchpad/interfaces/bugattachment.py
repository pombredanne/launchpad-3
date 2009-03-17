# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Bug attachment interfaces."""

__metaclass__ = type

__all__ = [
    'BugAttachmentType',
    'IBugAttachment',
    'IBugAttachmentSet',
    'IBugAttachmentEditForm',
    ]

from zope.interface import Interface
from zope.schema import Bool, Bytes, Choice, Int, TextLine
from lazr.enum import DBEnumeratedType, DBItem

from canonical.launchpad.interfaces.message import IMessage
from canonical.launchpad.interfaces.launchpad import IHasBug

from canonical.launchpad.fields import Title
from canonical.launchpad import _

from canonical.lazr.fields import Reference
from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, export_write_operation, exported)


class BugAttachmentType(DBEnumeratedType):
    """Bug Attachment Type.

    An attachment to a bug can be of different types, since for example
    a patch is more important than a screenshot. This schema describes the
    different types.
    """

    PATCH = DBItem(1, """
        Patch

        A patch that potentially fixes the bug.
        """)

    UNSPECIFIED = DBItem(2, """
        Unspecified

        Any attachment other than a patch. For example: a screenshot,
        a log file, a core dump, or anything else that adds more information
        to the bug.
        """)


class IBugAttachment(IHasBug):
    """A file attachment to an IBug."""
    export_as_webservice_entry()

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = exported(
        Reference(Interface, title=_('The bug the attachment belongs to.')))
    type = exported(
        Choice(
            title=_('Attachment Type'),
            description=_('The type of the attachment, for example Patch or '
                          'Unspecified.'),
            vocabulary=BugAttachmentType,
            default=BugAttachmentType.UNSPECIFIED,
            required=True))
    title = exported(
        Title(title=_('Title'),
              description=_(
                'A short and descriptive description of the attachment'),
              required=True))
    libraryfile = Bytes(title=_("The attachment content."),
              required=True)
    data = exported(
        Bytes(title=_("The attachment content."),
              required=True,
              readonly=True))
    message = exported(
        Reference(IMessage, title=_("The message that was created when we "
                                    "added this attachment.")))

    @export_write_operation()
    def removeFromBug():
        """Remove the attachment from the bug."""


# Need to do this here because of circular imports.
IMessage['bugattachments'].value_type.schema = IBugAttachment


class IBugAttachmentSet(Interface):
    """A set for IBugAttachment objects."""

    def create(bug, filealias, title, message,
               type=IBugAttachment['type'].default, send_notifications=False):
        """Create a new attachment and return it.

        :param bug: The `IBug` to which the new attachment belongs.
        :param filealias: The `IFilealias` containing the data.
        :param message: The `IMessage` to which this attachment belongs.
        :param type: The type of attachment. See `BugAttachmentType`.
        :param send_notifications: If True, a notification is sent to
            subscribers of the bug.
        """

    def __getitem__(id):
        """Get an IAttachment by its id.

        Return NotFoundError if no such id exists.
        """


class IBugAttachmentEditForm(Interface):
    """Schema used to build the edit form for bug attachments."""

    title = IBugAttachment['title']
    contenttype = TextLine(
        title=u'Content Type',
        description=(
            u"The content type is only settable if the attachment isn't "
            "a patch. If it's a patch, the content type will be set to "
            "text/plain"),
        required=True)
    patch = Bool(
        title=u"This attachment is a patch",
        required=True, default=False)

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug attachment interfaces."""

__metaclass__ = type

__all__ = [
    'IBugAttachment',
    'IBugAttachmentSet',
    'IBugAttachmentEditForm',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Object, Choice, Int, TextLine, Text, Bytes, Bool

from canonical.lp import dbschema
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.launchpad import IHasBug

from canonical.launchpad.fields import Title
from canonical.launchpad import _

class IBugAttachment(IHasBug):
    """A file attachment to an IBug."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Attribute('The bug the attachment belongs to.')
    type = Choice(
        title=_('Attachment Type'),
        description=_(
            'The type of the attachment, for example Patch or Unspecified.'),
        vocabulary="BugAttachmentType",
        default=dbschema.BugAttachmentType.UNSPECIFIED,
        required=True)
    title = Title(
        title=_('Title'),
        description=_('A short and descriptive description of the attachment'),
        required=True)
    libraryfile = Object(
        schema=ILibraryFileAlias,
        title=_("File"),
        description=_("The attachment."),
        required=True,
        )
    message = Attribute(
        "The message that was created when we added this attachment.")

    def removeFromBug():
        """Remove the attachment from the bug."""


class IBugAttachmentSet(Interface):
    """A set for IBugAttachment objects."""

    def create(bug, filealias, title, message,
               type=IBugAttachment['type'].default):
        """Create a new attachment and return it."""

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
        title=u"Patch",
        description=u"Check this box if the attachment is a patch.",
        required=True, default=False)

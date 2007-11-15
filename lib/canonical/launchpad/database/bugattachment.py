# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugAttachment', 'BugAttachmentSet']

from zope.event import notify
from zope.interface import implements

from sqlobject import ForeignKey, StringCol, SQLObjectNotFound

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.event.sqlobjectevent import SQLObjectDeletedEvent
from canonical.launchpad.interfaces import (
    BugAttachmentType, IBugAttachmentSet, IBugAttachment, NotFoundError)


class BugAttachment(SQLBase):
    """A bug attachment."""

    implements(IBugAttachment)

    _table = 'BugAttachment'

    bug = ForeignKey(
        foreignKey='Bug', dbName='bug', notNull=True)
    type = EnumCol(
        schema=BugAttachmentType, notNull=True,
        default=IBugAttachment['type'].default)
    title = StringCol(notNull=True)
    libraryfile = ForeignKey(
        foreignKey='LibraryFileAlias', dbName='libraryfile', notNull=True)
    message = ForeignKey(
        foreignKey='Message', dbName='message', notNull=True)

    def removeFromBug(self):
        """See IBugAttachment."""
        notify(SQLObjectDeletedEvent(self))
        self.destroySelf()

class BugAttachmentSet:
    """A set for bug attachments."""

    implements(IBugAttachmentSet)

    def __getitem__(self, attach_id):
        """See IBugAttachmentSet."""
        try:
            attach_id = int(attach_id)
        except ValueError:
            raise NotFoundError(attach_id)
        try:
            item = BugAttachment.get(attach_id)
        except SQLObjectNotFound:
            raise NotFoundError(attach_id)
        return item

    def create(self, bug, filealias, title, message,
               attach_type=None):
        """See IBugAttachmentSet."""
        if attach_type is None:
            # XXX kiko 2005-08-03 bug=1659: this should use DEFAULT.
            attach_type = IBugAttachment['type'].default
        return BugAttachment(
            bug=bug, libraryfile=filealias, type=attach_type, title=title,
            message=message)


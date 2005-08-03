# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugAttachment', 'BugAttachmentSet']

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import ForeignKey, StringCol, SQLObjectNotFound

from canonical.lp import dbschema
from canonical.lp.dbschema import EnumCol
from canonical.launchpad.interfaces import IBugAttachmentSet, IBugAttachment
from canonical.database.sqlbase import SQLBase


class BugAttachment(SQLBase):
    """A bug attachment."""

    implements(IBugAttachment)

    _table = 'BugAttachment'

    bug = ForeignKey(
        foreignKey='Bug', dbName='bug', notNull=True)
    type = EnumCol(
        schema=dbschema.BugAttachmentType, notNull=True,
        default=IBugAttachment['type'].default)
    title = StringCol(notNull=True)
    libraryfile = ForeignKey(
        foreignKey='LibraryFileAlias', dbName='libraryfile', notNull=True)
    message = ForeignKey(
        foreignKey='Message', dbName='message', notNull=True)


class BugAttachmentSet:
    """A set for bug attachments."""

    implements(IBugAttachmentSet)

    def __getitem__(self, id):
        """See IBugAttachmentSet."""
        try:
            id = int(id)
        except ValueError:
            raise NotFoundError(id)
        try:
            item = BugAttachment.get(id)
        except SQLObjectNotFound:
            raise NotFoundError(id)
        return item

    def create(self, bug, filealias, title, message,
               type=IBugAttachment['type'].default):
        """See IBugAttachmentSet."""
        return BugAttachment(
            bug=bug, libraryfile=filealias, type=type, title=title,
            message=message)

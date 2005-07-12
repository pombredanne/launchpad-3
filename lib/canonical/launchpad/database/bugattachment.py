# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugAttachment', 'BugAttachmentSet', 'BugAttachmentFactory',
           'BugAttachmentContentFactory']

from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, StringCol

from canonical.launchpad.database.bugset import BugSetBase
from canonical.launchpad.interfaces import IBugAttachmentSet, IBugAttachment
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol


class BugAttachment(SQLBase):
    """A bug attachment."""

    implements(IBugAttachment)

    _table = 'BugAttachment'

    message = ForeignKey(foreignKey='Message', dbName='message', notNull=True)
    name = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False, default=None)
    libraryfile = ForeignKey(foreignKey='LibraryFileAlias',
                             dbName='libraryfile', notNull=False)
    datedeactivated = UtcDateTimeCol(notNull=False, default=None)

class BugAttachmentSet(BugSetBase):
    """A set for bug attachments."""

    implements(IBugAttachmentSet)
    table = BugAttachment

    def __init__(self, bug=None):
        self.bug = bug

    def __getitem__(self, id):
        item = self.table.selectOne(self.table.q.id == id)
        if item is None:
            raise KeyError, id
        return item

    def __iter__(self):
        for row in self.table.select(self.table.q.bug == self.bug):
            yield row


def BugAttachmentFactory(context, **kw):
    bug = context.context.bug # view.attachmentcontainer.bug
    return BugAttachment(bug=bug, **kw)


def BugAttachmentContentFactory(context, **kw):
    bugattachment= context.context.id # view.attachment.id
    return BugAttachmentContent(
            bugattachment=bugattachment,
            daterevised=UTC_NOW,
            **kw
            )


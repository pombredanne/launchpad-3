
# Zope
from zope.interface import implements
# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.database.bug import BugContainerBase

from canonical.launchpad.interfaces.bugattachment import \
        IBugAttachment, IBugAttachmentContainer, IMaloneBugAttachment

from canonical.database.sqlbase import SQLBase


class BugAttachment(SQLBase):
    """A bug attachment."""

    implements(IBugAttachment)

    _table = 'BugAttachment'
    bugmessage = ForeignKey(foreignKey='BugMessage',
                            dbName='bugmessage', notNull=True)
    name = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False, default=None)
    libraryfile = ForeignKey(foreignKey='LibraryFileAlias',
                             dbName='libraryfile', notNull=False)
    datedeactivated = DateTimeCol(notNull=False, default=None)


class MaloneBugAttachment(BugAttachment, BugContainerBase):
    implements(IMaloneBugAttachment)
    _table = 'BugAttachment'


class BugAttachmentContainer(BugContainerBase):
    """A container for bug attachments."""

    implements(IBugAttachmentContainer)
    table = MaloneBugAttachment

    def __init__(self, bug=None):
        self.bug = bug

    def __getitem__(self, id):
        try:
            return self.table.select(self.table.q.id == id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select(self.table.q.bug == self.bug):
            yield row


def BugAttachmentFactory(context, **kw):
    bug = context.context.bug # view.attachmentcontainer.bug
    return MaloneBugAttachment(bug=bug, **kw)


def BugAttachmentContentFactory(context, **kw):
    bugattachment= context.context.id # view.attachment.id
    daterevised = datetime.utcnow()
    return BugAttachmentContent(
            bugattachment=bugattachment,
            daterevised=daterevised,
            **kw
            )



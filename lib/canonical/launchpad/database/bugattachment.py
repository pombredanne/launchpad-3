
# Zope
from zope.interface import implements
# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces.bugattachment import IBugAttachment

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


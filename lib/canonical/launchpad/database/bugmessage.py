
# Zope
from zope.interface import implements
# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces.bugmessage import IBugMessage

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC


class BugMessage(SQLBase):
    """A message for a bug."""

    implements(IBugMessage)

    _table = 'BugMessage'
    _defaultOrder = '-id'
    bug = ForeignKey(foreignKey='Bug', dbName='bug', notNull=True)
    datecreated = DateTimeCol(notNull=True)
    title = StringCol(notNull=True)
    contents = StringCol(notNull=True)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    parent = ForeignKey(foreignKey='BugMessage', dbName='parent', notNull=True)
    distribution = ForeignKey(foreignKey='Distribution',
                            dbName='distribution', notNull=False, default=None)
    rfc822msgid = StringCol(unique=True, notNull=True)

    attachments = MultipleJoin('BugAttachment', joinColumn='bugmessage')



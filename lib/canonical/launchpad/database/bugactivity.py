
# Zope
from zope.interface import implements
# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBugActivity

from canonical.database.sqlbase import SQLBase

class BugActivity(SQLBase):
    """Bug activity log entry."""

    implements(IBugActivity)

    _table = 'BugActivity'
    bug = ForeignKey(foreignKey='BugActivity',
                dbName='bug', notNull=True)
    datechanged = DateTimeCol(notNull=True)
    person = IntCol(notNull=True)
    whatchanged = StringCol(notNull=True)
    oldvalue = StringCol(default=None)
    newvalue = StringCol(default=None)
    message = StringCol(default=None)

        

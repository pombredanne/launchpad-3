
# Zope
from zope.interface import implements
# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces.bugsubscription import IBugSubscription

from canonical.database.sqlbase import SQLBase

class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table='BugSubscription'
    person = ForeignKey(dbName='person', foreignKey='Person',
                notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    subscription = IntCol(notNull=True)


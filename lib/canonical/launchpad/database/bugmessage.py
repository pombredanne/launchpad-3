# Zope
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey

from canonical.launchpad.interfaces import IBugMessage
from canonical.database.sqlbase import SQLBase

class BugMessage(SQLBase):
    """A table linking bugs and messages."""

    implements(IBugMessage)

    _table = 'BugMessage'

    # db field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)


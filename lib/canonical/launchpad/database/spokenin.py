# Zope
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import ISpokenIn

from canonical.database.sqlbase import SQLBase

#
# CONTENT CLASSES
#

class SpokenIn(SQLBase):
    """A way of telling which languages are spoken in which countries. This
    table maps a language which is SpokenIn a country."""

    implements(ISpokenIn)

    _table = 'SpokenIn'

    country = ForeignKey(dbName='country', notNull=True,
                         foreignKey='Country')
    language = ForeignKey(dbName='language', notNull=True,
                          foreignKey='Language')


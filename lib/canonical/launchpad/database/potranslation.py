# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import StringCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
from canonical.launchpad.interfaces import IPOTranslation


class POTranslation(SQLBase):
    implements(IPOTranslation)

    _table = 'POTranslation'

    # alternateID=False because we have to select by hash in order to do
    # index lookups.
    translation = StringCol(dbName='translation', notNull=True, unique=True,
        alternateID=False)

    def byTranslation(cls, key):
        '''Return a POTranslation object for the given translation'''

        # We can't search directly on msgid, because this database column
        # contains values too large to index. Instead we search on its
        # hash, which *is* indexed
        r = POTranslation.select('sha1(translation) = sha1(%s)' % quote(key))
        assert r.count() in (0,1), 'Database constraint broken'
        if r.count() == 1:
            return r[0]
        else:
            # To be 100% compatible with the alternateID behaviour, we should
            # raise SQLObjectNotFound instead of KeyError
            raise SQLObjectNotFound(key)
    byTranslation = classmethod(byTranslation)

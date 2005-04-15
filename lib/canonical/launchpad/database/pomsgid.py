# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import StringCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
from canonical.launchpad.interfaces import IPOMsgID


class POMsgID(SQLBase):
    implements(IPOMsgID)

    _table = 'POMsgID'

    # alternateID is technically true, but we don't use it because this
    # column is too large to be indexed.
    msgid = StringCol(dbName='msgid', notNull=True, unique=True,
        alternateID=False)

    def byMsgid(cls, key):
        '''Return a POMsgID object for the given msgid'''

        # We can't search directly on msgid, because this database column
        # contains values too large to index. Instead we search on its
        # hash, which *is* indexed
        r = POMsgID.select('sha1(msgid) = sha1(%s)' % quote(key))
        assert r.count() in (0,1), 'Database constraint broken'
        if r.count() == 1:
            return r[0]
        else:
            # To be 100% compatible with the alternateID behaviour, we should
            # raise SQLObjectNotFound instead of KeyError
            raise SQLObjectNotFound(key)
    byMsgid = classmethod(byMsgid)

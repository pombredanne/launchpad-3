# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['POTranslation']

from zope.interface import implements

from sqlobject import StringCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.interfaces import IPOTranslation


class POTranslation(SQLBase):
    implements(IPOTranslation)

    _table = 'POTranslation'

    # alternateID=False because we have to select by hash in order to do
    # index lookups.
    translation = StringCol(dbName='translation', notNull=True, unique=True,
        alternateID=False)

    def byTranslation(cls, key):
        """Return a POTranslation object for the given translation."""

        # We can't search directly on msgid, because this database column
        # contains values too large to index. Instead we search on its
        # hash, which *is* indexed
        r = cls.selectOne('sha1(translation) = sha1(%s)' % quote(key))

        if r is not None:
            return r
        else:
            # To be 100% compatible with the alternateID behaviour, we should
            # raise SQLObjectNotFound instead of KeyError
            raise SQLObjectNotFound(key)

    byTranslation = classmethod(byTranslation)

    def getOrCreateTranslation(cls, key):
        """Return a POTranslation object for the given translation, or create
        it if it doesn't exist.
        """

        try:
            return cls.byTranslation(key)
        except SQLObjectNotFound:
            return cls(translation=key)

    getOrCreateTranslation = classmethod(getOrCreateTranslation)


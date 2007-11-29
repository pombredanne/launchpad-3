# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['GPGKey', 'GPGKeySet']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    ForeignKey, IntCol, StringCol, BoolCol, SQLObjectNotFound)

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.launchpad.interfaces import (
    IGPGKeySet, IGPGHandler, IGPGKey, GPGKeyAlgorithm)


class GPGKey(SQLBase):
    implements(IGPGKey)

    _table = 'GPGKey'

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    keyid = StringCol(dbName='keyid', notNull=True)
    fingerprint = StringCol(dbName='fingerprint', notNull=True)

    keysize = IntCol(dbName='keysize', notNull=True)

    algorithm = EnumCol(dbName='algorithm', notNull=True,
                        enum=GPGKeyAlgorithm)

    active = BoolCol(dbName='active', notNull=True)

    can_encrypt = BoolCol(dbName='can_encrypt', notNull=False)

    @property
    def keyserverURL(self):
        return getUtility(
            IGPGHandler).getURLForKeyInServer(self.fingerprint, public=True)

    @property
    def displayname(self):
        return '%s%s/%s' % (self.keysize, self.algorithm.title, self.keyid)


class GPGKeySet:
    implements(IGPGKeySet)

    def new(self, ownerID, keyid, fingerprint, keysize,
            algorithm, active=True, can_encrypt=False):
        """See IGPGKeySet"""
        return GPGKey(owner=ownerID, keyid=keyid,
                      fingerprint=fingerprint, keysize=keysize,
                      algorithm=algorithm, active=active,
                      can_encrypt=can_encrypt)

    def get(self, key_id, default=None):
        """See IGPGKeySet"""
        try:
            return GPGKey.get(key_id)
        except SQLObjectNotFound:
            return default

    def getByFingerprint(self, fingerprint, default=None):
        """See IGPGKeySet"""
        result = GPGKey.selectOneBy(fingerprint=fingerprint)
        if result is None:
            return default
        return result

    def getGPGKeys(self, ownerid=None, active=True):
        """See IGPGKeySet"""
        if active is False:
            query = """
                active = false
                AND fingerprint NOT IN
                    (SELECT fingerprint FROM LoginToken
                     WHERE fingerprint IS NOT NULL
                           AND requester = %s
                           AND date_consumed is NULL
                    )
                """ % sqlvalues(ownerid)
        else:
            query = 'active=true'

        if ownerid:
            query += ' AND owner=%s' % sqlvalues(ownerid)

        return GPGKey.select(query, orderBy='id')



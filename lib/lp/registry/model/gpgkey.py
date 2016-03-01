# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['GPGKey', 'GPGKeySet']

from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLObjectNotFound,
    StringCol,
    )
from zope.component import getUtility
from zope.interface import implementer

from lp.registry.interfaces.gpg import (
    IGPGKey,
    IGPGKeySet,
    )
from lp.services.database.enumcol import EnumCol
from lp.services.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from lp.services.features import getFeatureFlag
from lp.services.gpg.interfaces import (
    GPG_WRITE_TO_GPGSERVICE_FEATURE_FLAG,
    GPGKeyAlgorithm,
    IGPGClient,
    IGPGHandler,
    )
from lp.services.openid.interfaces.openid import IOpenIDPersistentIdentity
from lp.services.openid.model.openididentifier import OpenIdIdentifier


@implementer(IGPGKey)
class GPGKey(SQLBase):

    _table = 'GPGKey'
    _defaultOrder = ['owner', 'keyid']

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


@implementer(IGPGKey)
class GPGServiceKey:

    def __init__(self, key_data):
        self._key_data = key_data

    @property
    def keysize(self):
        return self._key_data['size']

    @property
    def algorithm(self):
        return GPGKeyAlgorithm[self._key_data['algorithm']]

    @property
    def keyid(self):
        return self._key_data['id']

    @property
    def fingerprint(self):
        return self._key_data['fingerprint']

    @property
    def active(self):
        return self._key_data['enabled']

    @property
    def displayname(self):
        return '%s%s/%s' % (self.keysize, self.algorithm.title, self.keyid)

    @property
    def keyserverURL(self):
        return getUtility(
            IGPGHandler).getURLForKeyInServer(self.fingerprint, public=True)

    @property
    def can_encrypt(self):
        return self._key_data['can_encrypt']

    @property
    def owner(self):
        return getUtility(IPersonSet).getByOpenIDIdentifier(
            self._key_data['owner'])

    @property
    def ownerID(self):
        return self.owner.id



@implementer(IGPGKeySet)
class GPGKeySet:

    def new(self, ownerID, keyid, fingerprint, keysize,
            algorithm, active=True, can_encrypt=False):
        """See `IGPGKeySet`"""
        key = GPGKey(owner=ownerID, keyid=keyid,
                      fingerprint=fingerprint, keysize=keysize,
                      algorithm=algorithm, active=active,
                      can_encrypt=can_encrypt)
        return key

    def activate(self, requester, key, can_encrypt):
        """See `IGPGKeySet`."""
        fingerprint = key.fingerprint
        lp_key = self.getByFingerprint(fingerprint)
        if lp_key:
            is_new = False
            # Then the key already exists, so let's reactivate it.
            lp_key.active = True
            lp_key.can_encrypt = can_encrypt
        else:
            is_new = True
            ownerID = requester.id
            keyid = key.keyid
            keysize = key.keysize
            algorithm = GPGKeyAlgorithm.items[key.algorithm]
            lp_key = self.new(
                ownerID, keyid, fingerprint, keysize, algorithm,
                can_encrypt=can_encrypt)
        if getFeatureFlag(GPG_WRITE_TO_GPGSERVICE_FEATURE_FLAG):
            client = getUtility(IGPGClient)
            openid_identifier = self.getOwnerIdForPerson(lp_key.owner)
            client.addKeyForOwner(openid_identifier, key.fingerprint)
        return lp_key, is_new

    def deactivate(self, key):
        key.active = False
        if getFeatureFlag(GPG_WRITE_TO_GPGSERVICE_FEATURE_FLAG):
            client = getUtility(IGPGClient)
            openid_identifier = self.getOwnerIdForPerson(key.owner)
            client.disableKeyForOwner(openid_identifier, key.fingerprint)

    def getByFingerprint(self, fingerprint, default=None):
        """See `IGPGKeySet`"""
        result = GPGKey.selectOneBy(fingerprint=fingerprint)
        if result is None:
            return default
        return result

    def getGPGKeysForPerson(self, owner, active=True):
        if active is False:
            query = """
                active = false
                AND fingerprint NOT IN
                    (SELECT fingerprint FROM LoginToken
                     WHERE fingerprint IS NOT NULL
                           AND requester = %s
                           AND date_consumed is NULL
                    )
                """ % sqlvalues(owner.id)
        else:
            query = 'active=true'

        query += ' AND owner=%s' % sqlvalues(owner.id)

        return GPGKey.select(query, orderBy='id')

    def getOwnerIdForPerson(self, owner):
        """See IGPGKeySet."""
        return IOpenIDPersistentIdentity(owner).openid_identity_url

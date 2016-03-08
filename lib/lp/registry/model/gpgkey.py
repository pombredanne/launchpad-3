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
from lp.registry.interfaces.person import IPersonSet
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from lp.services.features import getFeatureFlag
from lp.services.gpg.interfaces import (
    GPG_WRITE_TO_GPGSERVICE_FEATURE_FLAG,
    GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG,
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
        self.active = key_data['enabled']

    @property
    def keysize(self):
        return self._key_data['size']

    @property
    def algorithm(self):
        return GPGKeyAlgorithm.items[self._key_data['algorithm']]

    @property
    def keyid(self):
        return self._key_data['id']

    @property
    def fingerprint(self):
        return self._key_data['fingerprint']

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
        # XXX: This is a little ugly - we can't use getByFingerprint here since
        # if the READ_FROM_GPGSERVICE FF is set we'll get a GPGServiceKey object
        # instead of a GPGKey object, and we need to change the database
        # representation in all cases.
        lp_key = GPGKey.selectOneBy(fingerprint=fingerprint)
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
            # XXX: Further to the comment above, if WRITE_TO_GPGSERVICE FF is
            # set then we need to duplicate the block above bur reading from
            # the gpgservice.
            client = getUtility(IGPGClient)
            if getFeatureFlag(GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG):
                lp_key = self.getByFingerprint(key.fingerprint)
                is_new = lp_key is None
                # TODO: make addKeyForOwner return the newly added key?
                client.addKeyForOwner(self.getOwnerIdForPerson(requester), key.fingerprint)
                lp_key = self.getByFingerprint(key.fingerprint)
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
        if getFeatureFlag(GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG):
            key_data = getUtility(IGPGClient).getKeyByFingerprint(fingerprint)
            return GPGServiceKey(key_data) if key_data else default
        else:
            result = GPGKey.selectOneBy(fingerprint=fingerprint)
            if result is None:
                return default
            return result

    def getByFingerprints(self, fingerprints):
        """See `IGPGKeySet`"""
        if getFeatureFlag(GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG):
            client = getUtility(IGPGClient)
            return client.getKeysByFingerprints(fingerprints)
        else:
            return IStore(GPGKey).find(
                GPGKey, GPGKey.fingerprint.is_in(fingerprints))

    def getGPGKeysForPerson(self, owner, active=True):
        if getFeatureFlag(GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG):
            client = getUtility(IGPGClient)
            owner_id = self.getOwnerIdForPerson(owner)
            keys = client.getKeysForOwner(owner_id)['keys']
            return [GPGServiceKey(d) for d in keys if d['enabled'] == active]
        else:
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

            return list(GPGKey.select(query, orderBy='id'))

    def getOwnerIdForPerson(self, owner):
        """See IGPGKeySet."""
        return IOpenIDPersistentIdentity(owner).openid_identity_url

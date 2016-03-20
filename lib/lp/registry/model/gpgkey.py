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
from lp.services.config import config
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
from lp.services.verification.interfaces.logintoken import ILoginTokenSet


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
    def active(self):
        return self._key_data['enabled']

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

    def __eq__(self, other):
        return self.fingerprint == other.fingerprint



@implementer(IGPGKeySet)
class GPGKeySet:

    def new(self, ownerID, keyid, fingerprint, keysize,
            algorithm, active=True, can_encrypt=False):
        """See `IGPGKeySet`"""
        return GPGKey(owner=ownerID, keyid=keyid,
                      fingerprint=fingerprint, keysize=keysize,
                      algorithm=algorithm, active=active,
                      can_encrypt=can_encrypt)

    def activate(self, requester, key, can_encrypt):
        """See `IGPGKeySet`."""
        assert key.owner == requester
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
            # XXX: Further to the comment above, if READ_FROM_GPGSERVICE FF is
            # set then we need to duplicate the block above but reading from
            # the gpgservice instead of the database:
            client = getUtility(IGPGClient)
            owner_id = self.getOwnerIdForPerson(requester)
            # Users with more than one openid identifier may be re-activating
            # a key that was previously deactivated with their non-default
            # openid identifier. If that's the case, use the same openid
            # identifier rather than the default one - this happens even if the
            # read FF is not set:
            key_data = client.getKeyByFingerprint(fingerprint)
            if key_data:
                owner_id = key_data['owner']
            allowed_owner_ids = self._getAllOwnerIdsForPerson(requester)
            assert owner_id in allowed_owner_ids
            gpgservice_key = GPGServiceKey(client.addKeyForOwner(owner_id, key.fingerprint))
            if getFeatureFlag(GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG):
                is_new == key_data is not None
                lp_key = gpgservice_key
        return lp_key, is_new

    def deactivate(self, key):
        # key could be a GPGServiceKey, which doesn't allow us to set it's
        # active attribute. Retrieve it by fingerprint:
        lp_key = GPGKey.selectOneBy(fingerprint=key.fingerprint)
        lp_key.active = False
        if getFeatureFlag(GPG_WRITE_TO_GPGSERVICE_FEATURE_FLAG):
            # Users with more than one openid identifier may be deactivating
            # a key that is associated with their non-default openid identifier.
            # If that's the case, use the same openid identifier rather than
            # the default one:
            client = getUtility(IGPGClient)
            key_data = client.getKeyByFingerprint(key.fingerprint)
            if not key_data:
                # We get here if we're asked to deactivate a key that was never
                # activated. This should probably never happen.
                return
            openid_identifier = key_data['owner']
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
        fingerprints = list(fingerprints)
        if getFeatureFlag(GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG):
            client = getUtility(IGPGClient)
            return [GPGServiceKey(key_data) for key_data in client.getKeysByFingerprints(fingerprints)]
        else:
            return list(IStore(GPGKey).find(
                GPGKey, GPGKey.fingerprint.is_in(fingerprints)))

    def getGPGKeysForPerson(self, owner, active=True):
        if getFeatureFlag(GPG_READ_FROM_GPGSERVICE_FEATURE_FLAG):
            client = getUtility(IGPGClient)
            owner_ids = self._getAllOwnerIdsForPerson(owner)
            if not owner_ids:
                return []
            gpg_keys = []
            for owner_id in owner_ids:
                key_data_list = client.getKeysForOwner(owner_id)['keys']
                gpg_keys.extend(
                    [GPGServiceKey(d) for d in key_data_list if d['enabled'] == active])
            if active is False:
                login_tokens = getUtility(ILoginTokenSet).getPendingGPGKeys(owner.id)
                token_fingerprints = [t.fingerprint for t in login_tokens]
                return [k for k in gpg_keys if k.fingerprint not in token_fingerprints]
            return gpg_keys
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
        url = IOpenIDPersistentIdentity(owner).openid_identity_url
        assert url is not None
        return url

    def _getAllOwnerIdsForPerson(self, owner):
        identifiers = IStore(OpenIdIdentifier).find(
            OpenIdIdentifier, account=owner.account)
        openid_provider_root = config.launchpad.openid_provider_root
        return [openid_provider_root + '+id/' + i.identifier.encode('ascii') for i in identifiers]

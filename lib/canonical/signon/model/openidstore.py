# Copyright 2009 Canonical Ltd.  All rights reserved.

"""OpenIDStore implementation for the SSO server's OpenID provider."""

__metaclass__ = type
__all__ = [
    'ProviderOpenIDStore',
    ]

from zope.interface import implements

from canonical.launchpad.database.baseopenidstore import (
    BaseStormOpenIDAssociation, BaseStormOpenIDNonce, BaseStormOpenIDStore)
from canonical.signon.interfaces.openidstore import IProviderOpenIDStore


class ProviderAssociation(BaseStormOpenIDAssociation):
    __storm_table__ = 'OpenIDAssociation'


class ProviderNonce(BaseStormOpenIDNonce):
    __storm_table__ = 'OpenIDNonce'


class ProviderOpenIDStore(BaseStormOpenIDStore):
    implements(IProviderOpenIDStore)

    Association = ProviderAssociation
    Nonce = ProviderNonce


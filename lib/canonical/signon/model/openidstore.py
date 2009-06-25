# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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
    """An association store for the OpenID Provider."""
    implements(IProviderOpenIDStore)

    Association = ProviderAssociation
    Nonce = ProviderNonce


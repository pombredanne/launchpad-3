# Copyright 2009 Canonical Ltd.  All rights reserved.

"""DBPolicy for the SSO service."""

__metaclass__ = type
__all__ = [
    'SSODatabasePolicy',
    ]


from canonical.launchpad.webapp.dbpolicy import BaseDatabasePolicy

from canonical.launchpad.webapp.interfaces import (
    AUTH_STORE, DisallowedStore, MAIN_STORE, MASTER_FLAVOR, SLAVE_FLAVOR)


class SSODatabasePolicy(BaseDatabasePolicy):
    """`IDatabasePolicy` for the single signon service.

    Only the auth Master and the main Slave are allowed. Requests for
    other Stores raise DisallowedStore exceptions.
    """
    config_section = 'sso'

    def getStore(self, name, flavor):
        """See `IDatabasePolicy`."""
        if name == AUTH_STORE:
            if flavor == SLAVE_FLAVOR:
                raise DisallowedStore(name, flavor)
            flavor = MASTER_FLAVOR
        elif name == MAIN_STORE:
            if flavor == MASTER_FLAVOR:
                raise DisallowedStore(name, flavor)
            flavor = SLAVE_FLAVOR
        else:
            raise DisallowedStore(name, flavor)

        return super(SSODatabasePolicy, self).getStore(name, flavor)



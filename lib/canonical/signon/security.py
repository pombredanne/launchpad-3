# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Security policies for SSO content objects."""

__metaclass__ = type
__all__ = []

from zope.component import getUtility

from lp.registry.interfaces.person import IPerson

from canonical.launchpad.security import AuthorizationBase
from canonical.launchpad.interfaces.launchpad import (
    ILaunchpadCelebrities)

from canonical.signon.interfaces.ssoaccount import ISSOAccount


class ViewSSOAccount(AuthorizationBase):
    usedfor = ISSOAccount
    permission = 'launchpad.View'

    def checkAccountAuthenticated(self, account):
        if account == self.obj.account:
            return True
        user = IPerson(account, None)
        return (user is not None and
                user.inTeam(getUtility(ILaunchpadCelebrities).admin))

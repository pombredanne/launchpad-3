# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SSOAccount']

from zope.component import adapts
from zope.interface import implements

from storm.locals import Desc
from storm.store import Store

from canonical.launchpad.interfaces import IMasterStore
from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.interfaces.authtoken import LoginTokenType

from canonical.signon.interfaces.ssoaccount import ISSOAccount
from canonical.signon.model.authtoken import AuthToken
from lp.services.openid.model.openidrpsummary import OpenIDRPSummary


class SSOAccount:
    """See `ISSOAccount`."""
    adapts(IAccount)
    implements(ISSOAccount)

    def __init__(self, account):
        self.account = account

    def getUnvalidatedEmails(self):
        """See `ISSOAccount`."""
        result = IMasterStore(AuthToken).find(
            AuthToken, requester_account=self.account,
            tokentype=LoginTokenType.VALIDATEEMAIL, date_consumed=None)
        return sorted(set(result.values(AuthToken.email)))

    @property
    def recently_authenticated_rps(self):
        """See `ISSOAccount`."""
        result = Store.of(self.account).find(
            OpenIDRPSummary, account=self.account)
        result.order_by(Desc(OpenIDRPSummary.date_last_used))
        return result.config(limit=10)


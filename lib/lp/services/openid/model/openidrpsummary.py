# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenIDRPSummary database classes."""

__metaclass__ = type
__all__ = [
    'OpenIDRPSummary',
    'OpenIDRPSummarySet',
    ]


from datetime import datetime

import pytz
from sqlobject import (
    ForeignKey,
    IntCol,
    StringCol,
    )
from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.webapp.url import urlparse
from canonical.launchpad.webapp.vhosts import allvhosts
from lp.services.openid.interfaces.openid import IOpenIDPersistentIdentity
from lp.services.openid.interfaces.openidrpsummary import (
    IOpenIDRPSummary,
    IOpenIDRPSummarySet,
    )


class OpenIDRPSummary(SQLBase):
    """A summary of the interaction between a `IAccount` and an OpenID RP."""
    implements(IOpenIDRPSummary)
    _table = 'OpenIDRPSummary'

    account = ForeignKey(dbName='account', foreignKey='Account', notNull=True)
    openid_identifier = StringCol(notNull=True)
    trust_root = StringCol(notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_last_used = UtcDateTimeCol(notNull=True, default=DEFAULT)
    total_logins = IntCol(notNull=True, default=1)

    def increment(self, date_used=None):
        """See `IOpenIDRPSummary`.

        :param date_used: an optional datetime the login happened. The current
            datetime is used if date_used is None.
        """
        self.total_logins = self.total_logins + 1
        if date_used is None:
            date_used = datetime.now(pytz.UTC)
        self.date_last_used = date_used


class OpenIDRPSummarySet:
    """A set of OpenID RP Summaries."""
    implements(IOpenIDRPSummarySet)

    def getByIdentifier(self, identifier, only_unknown_trust_roots=False):
        """See `IOpenIDRPSummarySet`."""
        # XXX: flacoste 2008-11-17 bug=274774: Normalize the trust_root
        # in OpenIDRPSummary.
        if only_unknown_trust_roots:
            result = OpenIDRPSummary.select("""
            CASE
                WHEN OpenIDRPSummary.trust_root LIKE '%%/'
                THEN OpenIDRPSummary.trust_root
                ELSE OpenIDRPSummary.trust_root || '/'
            END NOT IN (SELECT trust_root FROM OpenIdRPConfig)
            AND openid_identifier = %s
                """ % sqlvalues(identifier))
        else:
            result = OpenIDRPSummary.selectBy(openid_identifier=identifier)
        return result.orderBy('id')

    def _assert_identifier_is_not_reused(self, account, identifier):
        """Assert no other account in the summaries has the identifier."""
        summaries = OpenIDRPSummary.select("""
            account != %s
            AND openid_identifier = %s
            """ % sqlvalues(account, identifier))
        if summaries.count() > 0:
            raise AssertionError(
                'More than 1 account has the OpenID identifier of %s.' %
                identifier)

    def record(self, account, trust_root, date_used=None):
        """See `IOpenIDRPSummarySet`.

        :param date_used: an optional datetime the login happened. The current
            datetime is used if date_used is None.
        :raise AssertionError: If the account is not ACTIVE.
        :return: An `IOpenIDRPSummary` or None if the trust_root is
            Launchpad or one of its vhosts.
        """
        trust_site = urlparse(trust_root)[1]
        launchpad_site = allvhosts.configs['mainsite'].hostname
        if trust_site.endswith(launchpad_site):
            return None
        if account.status != AccountStatus.ACTIVE:
            raise AssertionError(
                'Account %d is not ACTIVE account.' % account.id)
        identifier = IOpenIDPersistentIdentity(account).openid_identity_url
        self._assert_identifier_is_not_reused(account, identifier)
        if date_used is None:
            date_used = datetime.now(pytz.UTC)
        summary = OpenIDRPSummary.selectOneBy(
            account=account, openid_identifier=identifier,
            trust_root=trust_root)
        if summary is not None:
            # Update the existing summary.
            summary.increment(date_used=date_used)
        else:
            # create a new summary.
            summary = OpenIDRPSummary(
                account=account, openid_identifier=identifier,
                trust_root=trust_root, date_created=date_used,
                date_last_used=date_used, total_logins=1)
        return summary

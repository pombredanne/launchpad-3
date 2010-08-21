# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenIDRPSummary related interfaces."""

__metaclass__ = type
__all__ = [
    'IOpenIDRPSummary',
    'IOpenIDRPSummarySet',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Datetime,
    Int,
    TextLine,
    )

from canonical.launchpad.interfaces.account import IAccount


class IOpenIDRPSummary(Interface):
    """A summary of the interaction between an `Account` and an OpenID RP."""
    id = Int(title=u'ID', required=True)
    account = Reference(
        title=u'The IAccount used to login.', schema=IAccount,
        required=True, readonly=True)
    openid_identifier = TextLine(
        title=u'OpenID identifier', required=True, readonly=True)
    trust_root = TextLine(
        title=u'OpenID trust root', required=True, readonly=True)
    date_created = Datetime(
        title=u'Date Created', required=True, readonly=True)
    date_last_used = Datetime(title=u'Date last used', required=True)
    total_logins = Int(title=u'Total logins', required=True)

    def increment(date_used=None):
        """Increment the total_logins.

        :param date_used: an optional datetime the login happened. The current
            datetime is used if date_used is None.
        """


class IOpenIDRPSummarySet(Interface):
    """A set of OpenID RP Summaries."""

    def getByIdentifier(identifier, only_unknown_trust_roots=False):
        """Get all the IOpenIDRPSummary objects for an OpenID identifier.

        :param identifier: A string used as an OpenID identifier.
        :param only_unknown_trust_roots: if True, only records for trust roots
            which there is no IOpenIDRPConfig entry will be returned.
        :return: An iterator of IOpenIDRPSummary objects.
        """

    def record(account, trust_root):
        """Create or update an IOpenIDRPSummary.

        :param account: An `IAccount`.
        :param trust_root: A string used as an OpenID trust root.
        :return: An `IOpenIDRPSummary` or None.
        """


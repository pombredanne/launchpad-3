# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211

__metaclass__ = type

__all__ = ['ISSOAccount']

from zope.interface import Interface
from zope.schema import List

from canonical.launchpad import _


class ISSOAccount(Interface):
    """IAccount with extra methods/attributes specific to the SSO."""

    recently_authenticated_rps = List(
        title=_("Most recently authenticated relying parties."),
        description=_(
            "A list of up to 10 `IOpenIDRPSummary` objects representing the "
            "OpenID Relying Parties in which this account authenticated "
            "most recently."),
        readonly=False, required=True)

    def getUnvalidatedEmails():
        """Get a list of the unvalidated email addresses for this account.

        An unvalidated email address is one which the user has tried
        to add to their account but has not yet replied to the
        corresponding confirmation email."""



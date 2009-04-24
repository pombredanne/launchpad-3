# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Bug subscription interfaces."""

__metaclass__ = type

__all__ = [
    'IBugSubscription',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Int
from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.interfaces.bug import IBug

from lazr.restful.declarations import (
    export_as_webservice_entry, exported)
from lazr.restful.fields import Reference

class IBugSubscription(Interface):
    """The relationship between a person and a bug."""

    export_as_webservice_entry()

    id = Int(title=_('ID'), readonly=True, required=True)
    person = exported(PublicPersonChoice(
        title=_('Person'), required=True, vocabulary='ValidPersonOrTeam',
        readonly=True, description=_("The person's Launchpad ID or "
        "e-mail address. You can only subscribe someone who has a Launchpad "
        "account.")))
    bug = exported(Reference(
        IBug, title=_("Bug"), required=True, readonly=True))
    subscribed_by = exported(PublicPersonChoice(
        title=_('Subscribed by'), required=True,
        vocabulary='ValidPersonOrTeam', readonly=True,
        description=_("The person who created this subscription.")))

    display_subscribed_by = Attribute(
        "`subscribed_by` formatted for display.")

    def canBeUnsubscribedByUser(user):
        """Can the user unsubscribe the subscriber form the bug?"""

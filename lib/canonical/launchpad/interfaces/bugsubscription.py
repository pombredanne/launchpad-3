# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Bug subscription interfaces."""

__metaclass__ = type

__all__ = [
    'IBugSubscription',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Int
from canonical.launchpad import _

class IBugSubscription(Interface):
    """The relationship between a person and a bug."""

    id = Int(title=_('ID'), readonly=True, required=True)
    person = Choice(
        title=_('Person'), required=True, vocabulary='ValidPersonOrTeam',
        readonly=True, description=_("The person's Launchpad ID or "
        "e-mail address. You can only subscribe someone who has a Launchpad "
        "account.")
        )
    bug = Int(title=_('Bug Number'), required=True, readonly=True)


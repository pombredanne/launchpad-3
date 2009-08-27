# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Bounty subscription interfaces."""

__metaclass__ = type

__all__ = [
    'IBountySubscription',
    'IBountySubscriptionSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Int
from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice

class IBountySubscription(Interface):
    """The relationship between a person and a bounty."""

    id = Int(title=_('ID'), readonly=True, required=True)
    person = PublicPersonChoice(
            title=_('Person ID'), required=True,
            vocabulary='ValidPersonOrTeam', readonly=True,
            )
    bounty = Int(title=_('Bounty ID'), required=True, readonly=True)


class IBountySubscriptionSet(Interface):
    """A set for IBountySubscription objects."""

    title = Attribute('Title')

    def __getitem__(key):
        """Get a BountySubscription object."""

    def __iter__():
        """Iterate over all bounty subscriptions."""

    def delete(id):
        """Delete a bounty subscription."""


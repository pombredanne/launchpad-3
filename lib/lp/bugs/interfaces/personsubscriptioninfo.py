# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Person's bug subscription information interfaces."""

__all__ = [
    'IPersonSubscriptionInfo',
    'IPersonSubscriptionInfoSet',
    'PersonSubscriptionType',
    ]


from canonical.launchpad import _
from lazr.enum import (
    EnumeratedType,
    Item,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Datetime,
    Int,
    )
from lp.services.fields import (
    BugField,
    PersonChoice,
    )


class PersonSubscriptionType(EnumeratedType):
    """Bug subscription type for a person."""

    DIRECT = Item(10, """
        Direct subscription or subscription through team membership
        on the bug.
        """)

    DUPLICATE = Item(20, """
        Direct subscription or team subscription on the duplicate.
        """)

    SUPERVISOR = Item(30, """
        Subscription as the bug supervisor.
        """)


class IPersonSubscriptionInfo(Interface):
    """Bug subscription information for a person."""

    subscription_type = Choice(
        title=_("Bug subscription type for a person"), required=True,
        vocabulary=PersonSubscriptionType,
        description=_("Type of a subscription that a person has "
                      "on this bug."))

    bug = BugField(
        title=_("Bug"), readonly=True, required=True,
        description=_("A bug that this subscription is on. "
                      "If subscription is on a duplicate "
                      "bug, references that bug."))

    person = PersonChoice(
        title=_("Subscriber"), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam',
        description=_("A real subscriber that person is "
                      "subscribed through.  Might be a person "
                      "itself or a team person is member of."))

    duplicates = Attribute(
        "List of duplicate bugs through which you have a subscription.")

    can_change_supervisor = Attribute(
        "List of duplicate bugs through which you have a subscription.")

    as_team_member = Attribute(
        "Teams through which this subscription is applicable. "
        "Excludes teams you are an admin of.")

    as_team_admin = Attribute(
        "Teams through which this subscription is applicable and "
        "which a person is an admin of.")


class IPersonSubscriptionInfoSet(Interface):
    """A utility for accessing `IPersonSubscriptionInfo` records."""

    def loadSubscriptionsFor(person, bug):
        """Load subscriptions for a person/bug."""

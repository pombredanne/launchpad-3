# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Person's bug subscription information interfaces."""

__all__ = [
    'IPersonSubscriptionInfo',
    'IPersonSubscriptions',
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
    Bool,
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

    personally = Bool(
        title=_("Personally subscribed"),
        description=_("Is subscribed directly (as opposed through a team)."),
        default=False, readonly=True)

    duplicates = Attribute(
        "List of duplicate bugs through which you have a subscription.")

    supervisor_for = Attribute(
        "Targets this person is a supervisor for.")

    owner_for = Attribute(
        "Targets this person is both a supervisor and owner for.")

    as_team_member = Attribute(
        "Teams through which this subscription is applicable. "
        "Excludes teams you are an admin of.")

    as_team_admin = Attribute(
        "Teams through which this subscription is applicable and "
        "which a person is an admin of.")


class IPersonSubscriptions(Interface):
    """Container for all `IPersonSubscriptionInfo`s for a (person, bug)."""

    direct_subscriptions = Attribute(
        "Contains information about all direct subscriptions, including "
        "those through membership in teams directly subscribed to a bug.")

    duplicate_subscriptions = Attribute(
        "Contains information about all subscriptions through duplicate "
        "bugs, including those through team membership.")

    supervisor_subscriptions = Attribute(
        "Contains information about all subscriptions as bug supervisor, "
        "including those through team memberships and target ownership "
        "when no bug supervisor is defined for the target.")

    def reload():
        """Reload subscriptions for a person/bug."""

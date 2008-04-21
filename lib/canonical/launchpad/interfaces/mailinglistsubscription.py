# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Mailing list interfaces related to list subscriptions."""

__metaclass__ = type

__all__ = ['MailingListAutoSubscribePolicy']


from canonical.lazr.enum import DBEnumeratedType, DBItem


class MailingListAutoSubscribePolicy(DBEnumeratedType):
    """A person's auto-subscription policy.

    When a person joins a team, or is joined to a team, their
    auto-subscription policy describes how and whether they will be
    automatically subscribed to any team mailing list that the team may have.

    This does not describe what happens when a team that already has members
    gets a new team mailing list.  In that case, its members are never
    automatically subscribed to the mailing list.
    """

    NEVER = DBItem(0, """
        Never subscribe automatically

        The user must explicitly subscribe to a team mailing list for any team
        that she joins.
        """)

    ON_REGISTRATION = DBItem(1, """
        Subscribe on self-registration

        The user is automatically joined to any team mailng list for a team
        that she joins explicitly.  She is never joined to any team mailing
        list for a team that someone else joins her to.
        """)

    ALWAYS = DBItem(2, """
        Always subscribe automatically

        The user is automatically subscribed to any team mailing list when she
        is added to the team, regardless of who joins her to the team.
        """)

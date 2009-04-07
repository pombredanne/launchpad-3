# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['JoinTeamEvent', 'TeamInvitationEvent']

from zope.interface import implements

from canonical.launchpad.event.interfaces import (
    IJoinTeamEvent, ITeamInvitationEvent)


class JoinTeamEvent:
    """See canonical.launchpad.event.interfaces.IJoinTeamEvent."""

    implements(IJoinTeamEvent)

    def __init__(self, person, team):
        self.person = person
        self.team = team


class TeamInvitationEvent:
    """See canonical.launchpad.event.interfaces.IJoinTeamEvent."""

    implements(ITeamInvitationEvent)

    def __init__(self, member, team):
        self.member = member
        self.team = team


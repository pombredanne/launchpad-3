# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['JoinTeamEvent']

from zope.interface import implements

from canonical.launchpad.event.interfaces import IJoinTeamEvent


class JoinTeamEvent:
    """See canonical.launchpad.event.interfaces.IJoinTeamEvent."""

    implements(IJoinTeamEvent)

    def __init__(self, user, team):
        self.user = user
        self.team = team


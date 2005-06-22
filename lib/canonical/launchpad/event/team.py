# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['JoinTeamRequestEvent']

from zope.interface import implements

from canonical.launchpad.event.interfaces import IJoinTeamRequestEvent


class JoinTeamRequestEvent:
    """See canonical.launchpad.event.interfaces.IJoinTeamRequestEvent."""

    implements(IJoinTeamRequestEvent)

    def __init__(self, user, team, appurl):
        self.user = user
        self.team = team
        self.appurl = appurl


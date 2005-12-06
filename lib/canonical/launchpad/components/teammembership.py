# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Zope interfaces
from zope.interface import implements
from zope.component import getUtility

# canonical imports
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces import ITeamMembershipSet
from canonical.launchpad.interfaces import ITeamMembershipSubset


class TeamMembershipSubset:

    implements(ITeamMembershipSubset)

    def __init__(self, team=None):
        self.team = team

    def getByPersonName(self, name, default=None):
        assert self.team is not None
        person = getUtility(IPersonSet).getByName(name)
        if person is None:
            # We tried to look up a member which didn't exist
            return None
        mset = getUtility(ITeamMembershipSet)
        return mset.getByPersonAndTeam(person.id, self.team.id, default)

    def getActiveMemberships(self):
        assert self.team is not None
        mset = getUtility(ITeamMembershipSet)
        return mset.getActiveMemberships(self.team.id)

    def getProposedMemberships(self):
        assert self.team is not None
        mset = getUtility(ITeamMembershipSet)
        return mset.getProposedMemberships(self.team.id)

    def getInactiveMemberships(self):
        assert self.team is not None
        mset = getUtility(ITeamMembershipSet)
        return mset.getInactiveMemberships(self.team.id)


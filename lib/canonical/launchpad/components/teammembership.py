# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Zope interfaces
from zope.interface import implements
from zope.component import getUtility

from canonical.lp.dbschema import TeamMembershipStatus

# canonical imports
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces import ITeamMembershipSet
from canonical.launchpad.interfaces import ITeamMembershipSubset


class TeamMembershipSubset:

    implements(ITeamMembershipSubset)

    def __init__(self, team=None):
        self.team = team

    def _getMembershipsByStatus(self, status):
        mset = getUtility(ITeamMembershipSet)
        return mset.getMemberships(self.team.id, status.value)

    def getByPersonName(self, name, default=None):
        assert self.team is not None
        person = getUtility(IPersonSet).getByName(name)
        mset = getUtility(ITeamMembershipSet)
        return mset.getByPersonAndTeam(person.id, self.team.id, default)

    def getActiveMemberships(self):
        assert self.team is not None
        status = TeamMembershipStatus.ADMIN
        admins = self._getMembershipsByStatus(status)

        status = TeamMembershipStatus.APPROVED
        members = self._getMembershipsByStatus(status)
        return admins + members

    def getProposedMemberships(self):
        assert self.team is not None
        return self._getMembershipsByStatus(TeamMembershipStatus.PROPOSED)

    def getInactiveMemberships(self):
        assert self.team is not None
        status = TeamMembershipStatus.EXPIRED
        expired = self._getMembershipsByStatus(status)

        status = TeamMembershipStatus.DEACTIVATED
        deactivated = self._getMembershipsByStatus(status)
        return expired + deactivated


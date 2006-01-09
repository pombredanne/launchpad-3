# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['TeamMembership', 'TeamMembershipSet', 'TeamParticipation']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import (
    ITeamMembership, ITeamParticipation, ITeamMembershipSet)

from canonical.lp.dbschema import EnumCol, TeamMembershipStatus


class TeamMembership(SQLBase):
    implements(ITeamMembership)

    _table = 'TeamMembership'
    _defaultOrder = 'id'

    team = ForeignKey(dbName='team', foreignKey='Person', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    reviewer = ForeignKey(dbName='reviewer', foreignKey='Person', default=None)
    status = EnumCol(
        dbName='status', notNull=True, schema=TeamMembershipStatus)
    datejoined = UtcDateTimeCol(dbName='datejoined', default=UTC_NOW,
                                notNull=True)
    dateexpires = UtcDateTimeCol(dbName='dateexpires', default=None)
    reviewercomment = StringCol(dbName='reviewercomment', default=None)

    @property
    def statusname(self):
        return self.status.title

    @property
    def is_admin(self):
        return self.status in [TeamMembershipStatus.ADMIN]

    @property
    def is_owner(self):
        return self.person.id == self.team.teamowner.id

    def isExpired(self):
        return self.status == TeamMembershipStatus.EXPIRED


class TeamMembershipSet:

    implements(ITeamMembershipSet)

    _defaultOrder = ['Person.displayname', 'Person.name']

    def getByPersonAndTeam(self, person, team, default=None):
        result = TeamMembership.selectOneBy(personID=person.id, teamID=team.id)
        if result is None:
            return default
        return result

    def getTeamMembersCount(self, team):
        return TeamMembership.selectBy(teamID=team.id).count()

    def _getMembershipsByStatuses(self, team, statuses, orderBy=None):
        if orderBy is None:
            orderBy = self._defaultOrder
        clauses = []
        for status in statuses:
            clauses.append("TeamMembership.status = %s" % sqlvalues(status))
        clauses = " OR ".join(clauses)
        query = ("(%s) AND Person.id = TeamMembership.person AND "
                 "TeamMembership.team = %d" % (clauses, team.id))
        return TeamMembership.select(query, clauseTables=['Person'],
                                     orderBy=orderBy)

    def getActiveMemberships(self, team, orderBy=None):
        statuses = [TeamMembershipStatus.ADMIN, TeamMembershipStatus.APPROVED]
        return self._getMembershipsByStatuses(
            team, statuses, orderBy=orderBy)

    def getInactiveMemberships(self, team, orderBy=None):
        statuses = [TeamMembershipStatus.EXPIRED,
                    TeamMembershipStatus.DEACTIVATED]
        return self._getMembershipsByStatuses(
            team, statuses, orderBy=orderBy)

    def getProposedMemberships(self, team, orderBy=None):
        statuses = [TeamMembershipStatus.PROPOSED]
        return self._getMembershipsByStatuses(
            team, statuses, orderBy=orderBy)


class TeamParticipation(SQLBase):
    implements(ITeamParticipation)

    _table = 'TeamParticipation'

    team = ForeignKey(foreignKey='Person', dbName='team', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)




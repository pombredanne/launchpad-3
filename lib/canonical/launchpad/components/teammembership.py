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
        mset = getUtility(ITeamMembershipSet)
        return mset.getByPersonAndTeam(person.id, self.team.id, default)


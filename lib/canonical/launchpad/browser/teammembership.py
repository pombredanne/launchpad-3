# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['TeamMembershipSubsetNavigation']

from canonical.launchpad.webapp import Navigation
from canonical.launchpad.interfaces import ITeamMembershipSubset


class TeamMembershipSubsetNavigation(Navigation):

    usedfor = ITeamMembershipSubset

    def traverse(self, name):
        return self.context.getByPersonName(name)


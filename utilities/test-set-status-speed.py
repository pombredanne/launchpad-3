#!/usr/bin/python -S
#
# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the speed of TeamMembership.setStatus()."""

import _pythonpath

import sys
import time
import transaction

from storm.store import Store

from zope.component import getUtility

from canonical.launchpad.scripts import execute_zcml_for_scripts
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.teammembership import (
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.testing.factory import LaunchpadObjectFactory

factory = LaunchpadObjectFactory()

# Shut up, pyflakes.
_pythonpath = _pythonpath


def make_hierarchy():
    print 'Starting make_hierarchy:', time.ctime()
    person_set = getUtility(IPersonSet)
    admin = person_set.getByEmail('admin@canonical.com')
    child = person_set.getByName('child')
    parent = person_set.getByName('parent')
    if child is None:
        child = factory.makePerson(name='child')
        parent = factory.makeTeam(name='parent')
    super_teams = []
    for i in range(90):
        super1 = factory.makeTeam()
        super2 = factory.makeTeam()
        super1.addMember(super2, admin, force_team_add=True)
        super2.addMember(parent, admin, force_team_add=True)
        super_teams.append(super1)
        super_teams.append(super2)
    for team in super_teams:
        for i in range(12000 / len(super_teams)):
            team.addMember(factory.makePerson(), admin)
    print 'Finished make_hierarchy:', time.ctime()
    return child, parent


def test_remove_member(parent, child):
    print 'Starting test_remove_member'
    start = time.time()
    person_set = getUtility(IPersonSet)
    admin = person_set.getByEmail('admin@canonical.com')
    membership_set = getUtility(ITeamMembershipSet)
    tm = membership_set.getByPersonAndTeam(child, parent)
    tm.setStatus(TeamMembershipStatus.DEACTIVATED, admin)
    print 'Finished test_remove_member: elapsed=%f' % (time.time() - start)


def main(arguments):
    """Run the script."""
    execute_zcml_for_scripts()
    transaction.begin()
    person_set = getUtility(IPersonSet)

    if person_set.getByName('child') is None:
        child, parent = make_hierarchy()
        transaction.commit()
    else:
        child = person_set.getByName('child')
        parent = person_set.getByName('parent')

    parent.addMember(child, parent.teamowner)
    print 'child:', child
    print 'parent:', parent
    test_remove_member(parent, child)

    transaction.commit()

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.database import Person


class TestPerson(LaunchpadFunctionalTestCase):

    def test_getDirectMemberIParticipateIn(self):
        sample_person = Person.byName('name12')
        warty_team = Person.byName('name20')
        ubuntu_team = Person.byName('ubuntu-team')
        # Sample Person is an active member of Warty Security Team which in
        # turn is a proposed member of Ubuntu Team. That means
        # sample_person._getDirectMemberIParticipateIn(ubuntu_team) won't
        # return anything.
        self.failUnless(sample_person in warty_team.activemembers)
        self.failUnless(warty_team in ubuntu_team.proposedmembers)
        self.failUnlessEqual(
            sample_person._getDirectMemberIParticipateIn(ubuntu_team), None)

        # If we make warty_team an active member of Ubuntu team, then the
        # _getDirectMemberIParticipateIn() call will actually return
        # warty_team.
        ubuntu_team.addMember(warty_team, reviewer=sample_person)
        flush_database_updates()
        self.failUnless(warty_team in ubuntu_team.activemembers)
        self.failUnlessEqual(
            sample_person._getDirectMemberIParticipateIn(ubuntu_team),
            warty_team)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


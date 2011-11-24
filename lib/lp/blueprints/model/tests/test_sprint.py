# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit test for sprints."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestSprintAttendancesSort(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_attendances(self):
        #Test the sorting of attendances to be by displayname rather than name
        sprint = self.factory.makeSprint()
        bob = self.factory.makePerson(name='zbob', displayname='Bob')
        ced = self.factory.makePerson(name='xed', displayname='ced')
        dave = self.factory.makePerson(name='wdave', displayname='Dave')
        sprint.attend(
            bob, sprint.time_starts, sprint.time_ends, True)
        sprint.attend(
            ced, sprint.time_starts, sprint.time_ends, True)
        sprint.attend(
            dave, sprint.time_starts, sprint.time_ends, True)
        attendances = [bob.displayname, ced.displayname, dave.displayname]
        people = [attendee.attendee.displayname for attendee in sprint.attendances]
        self.assertEqual(attendances, people)

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit test for sprints."""

__metaclass__ = type

from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestSpecifications(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_specifications_quantity(self):
        sprint = self.factory.makeSprint()
        for count in range(10):
            blueprint = self.factory.makeSpecification()
            link = blueprint.linkSprint(sprint, blueprint.owner)
            link.acceptBy(sprint.owner)
        self.assertEqual(10, sprint.specifications().count())
        self.assertEqual(10, sprint.specifications(quantity=None).count())
        self.assertEqual(8, sprint.specifications(quantity=8).count())
        self.assertEqual(10, sprint.specifications(quantity=11).count())


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

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for blueprints here."""

__metaclass__ = type

from testtools.matchers import Equals

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestSpecificationDependencies(TestCaseWithFactory):
    """Test the methods for getting the dependencies for blueprints."""

    layer = DatabaseFunctionalLayer

    def test_no_deps(self):
        blueprint = self.factory.makeBlueprint()
        self.assertThat(list(blueprint.dependencies), Equals([]))
        self.assertThat(list(blueprint.all_deps), Equals([]))
        self.assertThat(list(blueprint.blocked_specs), Equals([]))
        self.assertThat(list(blueprint.all_blocked), Equals([]))

    def test_single_dependency(self):
        do_first = self.factory.makeBlueprint()
        do_next = self.factory.makeBlueprint()
        do_next.createDependency(do_first)
        self.assertThat(list(do_first.blocked_specs), Equals([do_next]))
        self.assertThat(list(do_first.all_blocked), Equals([do_next]))
        self.assertThat(list(do_next.dependencies), Equals([do_first]))
        self.assertThat(list(do_next.all_deps), Equals([do_first]))

    def test_linear_dependency(self):
        do_first = self.factory.makeBlueprint()
        do_next = self.factory.makeBlueprint()
        do_next.createDependency(do_first)
        do_last = self.factory.makeBlueprint()
        do_last.createDependency(do_next)
        self.assertThat(sorted(do_first.blocked_specs), Equals([do_next]))
        self.assertThat(
            sorted(do_first.all_blocked),
            Equals(sorted([do_next, do_last])))
        self.assertThat(sorted(do_last.dependencies), Equals([do_next]))
        self.assertThat(
            sorted(do_last.all_deps),
            Equals(sorted([do_first, do_next])))

    def test_diamond_dependency(self):
        #             do_first
        #            /        \
        #    do_next_lhs    do_next_rhs
        #            \        /
        #             do_last
        do_first = self.factory.makeBlueprint()
        do_next_lhs = self.factory.makeBlueprint()
        do_next_lhs.createDependency(do_first)
        do_next_rhs = self.factory.makeBlueprint()
        do_next_rhs.createDependency(do_first)
        do_last = self.factory.makeBlueprint()
        do_last.createDependency(do_next_lhs)
        do_last.createDependency(do_next_rhs)
        self.assertThat(
            sorted(do_first.blocked_specs),
            Equals(sorted([do_next_lhs, do_next_rhs])))
        self.assertThat(
            sorted(do_first.all_blocked),
            Equals(sorted([do_next_lhs, do_next_rhs, do_last])))
        self.assertThat(
            sorted(do_last.dependencies),
            Equals(sorted([do_next_lhs, do_next_rhs])))
        self.assertThat(
            sorted(do_last.all_deps),
            Equals(sorted([do_first, do_next_lhs, do_next_rhs])))
            
class SpecificationSubscriptionSort(TestCaseWithFactory):
    
    layer = DatabaseFunctionalLayer
    
    def test_subscribers(self):
        #Test the sorting of subscribers to be by displayname rather than name
        spec = self.factory.makeBlueprint()
        bob = self.factory.makePerson(name='zbob', displayname='Bob')
        ced = self.factory.makePerson(name='xed', displayname='ced')
        dave = self.factory.makePerson(name='wdave', displayname='Dave')
        spec.subscribe(bob, bob, True)
        spec.subscribe(ced, bob, True)
        spec.subscribe(dave, bob, True)
        attendances = [bob.displayname, ced.displayname, dave.displayname]
        people = [sub.person.displayname for sub in spec.subscriptions]
        self.assertEqual(attendances, people)

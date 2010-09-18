# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for components and component groups (products) in bug trackers."""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.ftests import login_person
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestBugTrackerComponent(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTrackerComponent, self).setUp()

        regular_user = self.factory.makePerson()
        login_person(regular_user)

        self.bug_tracker = self.factory.makeBugTracker()

        self.comp_group = self.factory.makeBugTrackerComponentGroup(
            u'alpha',
            self.bug_tracker)

    def test_component_creation(self):
        """Verify a component can be created"""

        component = self.factory.makeBugTrackerComponent(
            u'example', self.comp_group)
        self.assertTrue(component is not None)
        self.assertEqual(component.name, u'example')

    def test_set_visibility(self):
        """Users can delete components

        In case invalid components get imported from a remote bug
        tracker, users can hide them so they don't show up in the UI.
        We do this rather than delete them outright so that they won't
        show up again when we re-sync from the remote bug tracker.
        """

        component = self.factory.makeBugTrackerComponent(
            u'example', self.comp_group)
        self.assertEqual(component.is_visible, True)

        component.hide()
        self.assertEqual(component.is_visible, False)

        component.show()
        self.assertEqual(component.is_visible, True)

    def test_custom_component(self):
        """Users can also add components

        For whatever reason, it may be that we can't import a component
        from the remote bug tracker.  This gives users a way to correct
        the omissions."""

        custom_component = self.factory.makeBugTrackerComponent(
            u'example', self.comp_group, custom=True)
        self.assertTrue(custom_component != None)
        self.assertEqual(custom_component.is_custom, True)

    def test_multiple_component_creation(self):
        """Verify several components can be created at once"""

        comp_a = self.factory.makeBugTrackerComponent(
            u'example-a', self.comp_group)
        comp_b = self.factory.makeBugTrackerComponent(
            u'example-b', self.comp_group)
        comp_c = self.factory.makeBugTrackerComponent(
            u'example-c', self.comp_group, True)

        self.assertTrue(comp_a is not None)
        self.assertTrue(comp_b is not None)
        self.assertTrue(comp_c is not None)


class TestBugTrackerWithComponents(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTrackerWithComponents, self).setUp()

        regular_user = self.factory.makePerson()
        login_person(regular_user)

        self.bug_tracker = self.factory.makeBugTracker()

    def test_empty_bugtracker(self):
        """Trivial case of bugtracker with no products or components"""

        self.assertTrue(self.bug_tracker is not None)

        # Empty bugtrackers shouldn't return component groups
        comp_group = self.bug_tracker.getRemoteComponentGroup(u'non-existant')
        self.assertEqual(comp_group, None)

        # Verify it contains no component groups
        comp_groups = self.bug_tracker.getAllRemoteComponentGroups()
        self.assertEqual(len(list(comp_groups)), 0)

    def test_single_product_bugtracker(self):
        """Bug tracker with a single (default) product and several components
        """

        # Add a component group and fill it with some components
        default_comp_group = self.bug_tracker.addRemoteComponentGroup(
            u'alpha')
        default_comp_group.addComponent(u'example-a')
        default_comp_group.addComponent(u'example-b')
        default_comp_group.addComponent(u'example-c')

        # Verify that retrieving an invalid component group returns nothing
        comp_group = self.bug_tracker.getRemoteComponentGroup(u'non-existant')
        self.assertEqual(comp_group, None)

        # Now retrieve the component group we added
        comp_group = self.bug_tracker.getRemoteComponentGroup(u'alpha')
        self.assertEqual(comp_group, default_comp_group)
        self.assertEqual(comp_group.name, u'alpha')

        # Verify there is only the one component group in the tracker
        comp_groups = self.bug_tracker.getAllRemoteComponentGroups()
        self.assertEqual(len(list(comp_groups)), 1)

    def test_multiple_product_bugtracker(self):
        """Bug tracker with multiple products and components"""

        # Create several component groups with varying numbers of components
        comp_group_i = self.bug_tracker.addRemoteComponentGroup(u'alpha')

        comp_group_ii = self.bug_tracker.addRemoteComponentGroup(u'beta')
        comp_group_ii.addComponent(u'example-beta-1')

        comp_group_iii = self.bug_tracker.addRemoteComponentGroup(u'gamma')
        comp_group_iii.addComponent(u'example-gamma-1')
        comp_group_iii.addComponent(u'example-gamma-2')
        comp_group_iii.addComponent(u'example-gamma-3')

        # Retrieving a non-existant component group returns nothing
        comp_group = self.bug_tracker.getRemoteComponentGroup(u'non-existant')
        self.assertEqual(comp_group, None)

        # Now retrieve one of the real component groups
        comp_group = self.bug_tracker.getRemoteComponentGroup(u'beta')
        self.assertEqual(comp_group, comp_group_ii)

        # Check the correct number of component groups are in the bug tracker
        comp_groups = self.bug_tracker.getAllRemoteComponentGroups()
        self.assertEqual(len(list(comp_groups)), 3)

    def test_get_components_for_component_group(self):
        """Retrieve a set of components from a given product"""

        # Create a component group with some components
        default_comp_group = self.bug_tracker.addRemoteComponentGroup(
            u'alpha')
        default_comp_group.addComponent(u'example-a')
        default_comp_group.addComponent(u'example-b')
        default_comp_group.addComponent(u'example-c')

        # Verify group has the correct number of components
        comp_group = self.bug_tracker.getRemoteComponentGroup(u'alpha')
        self.assertEqual(len(list(comp_group.components)), 3)

        # Check one of the components, that it is what we expect
        comp = comp_group.getComponent(u'example-b')
        self.assertEqual(comp.name, u'example-b')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))

    return suite

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for components and component groups (products) in bug trackers."""

__metaclass__ = type

__all__ = []

import unittest

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.launchpad.ftests import (
    login,
    login_person,
    ANONYMOUS,
    )
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory

from lp.bugs.interfaces.bugtracker import (
    IBugTracker,
    IBugTrackerComponent,
    IBugTrackerComponentGroup)


class TestBugTrackerComponent(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)
        super(TestBugTrackerComponent, self).setUp()
        self.comp_group = self.factory.makeBugTrackerComponentGroup()

    def test_component_creation(self):
        component = self.factory.makeBugTrackerComponent(
            "Foobar", self.comp_group)
        self.assertTrue(component != None)

    def test_set_visibility(self):
        component = self.factory.makeBugTrackerComponent(
            "Foobar", self.comp_group)
        self.assertEqual(component.is_visible, True)

        #TODO - only logged in users should be able to show/hide components
        # self.assertRaises(Unauthorized, getattr, self.component, 'hide')
        # regular_user = self.factory.makePerson()
        # login_person(regular_user)

        component.hide()
        self.assertEqual(component.is_visible, False)

        component.show()
        self.assertEqual(component.is_visible, True)
        
    def test_custom_component(self):
        custom_component = self.factory.makeBugTrackerComponent(
            "CustomComponent", self.comp_group, custom=True)
        self.assertTrue(custom_component != None)
        self.assertEqual(custom_component.is_custom, True)

    def test_multiple_component_creation(self):
        comp_a = self.factory.makeBugTrackerComponent(
            "a", self.comp_group)
        comp_b = self.factory.makeBugTrackerComponent(
            "b", self.comp_group)
        comp_c = self.factory.makeBugTrackerComponent(
            "c", self.comp_group, True)

        self.assertTrue(comp_a != None)
        self.assertTrue(comp_b != None)
        self.assertTrue(comp_c != None)


class TestBugTrackerWithComponents(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTrackerWithComponents, self).setUp()

        login(ANONYMOUS)
        self.bugtracker = self.factory.makeBugTracker()

    def test_empty_bugtracker(self):
        """Trivial case of bugtracker with no products or components"""
        self.assertTrue(self.bugtracker is not None)

        # Empty bugtrackers shouldn't return component groups
        comp_group = self.bugtracker.getRemoteComponentGroup('non-existant')
        self.assertEqual(comp_group, None)

        comp_groups = self.bugtracker.getAllRemoteComponentGroups()
        self.assertTrue(len(comp_groups) == 0)


    def test_single_product_bugtracker(self):
        """Bug tracker with a single (default) product and several components"""
        default_comp_group = self.bugtracker.addRemoteComponentGroup("Default")

        default_comp_group.addComponent("Alpha")
        default_comp_group.addComponent("Beta")
        default_comp_group.addComponent("Gamma")

        comp_group = self.bugtracker.getRemoteComponentGroup('non-existant')
#        self.assertEqual(comp_group, None)

        comp_group = self.bugtracker.getRemoteComponentGroup('Default')
#        self.assertEqual(comp_group, default_comp_group)
        #self.assertEqual(comp_group.name, "Default")

        comp_groups = self.bugtracker.getAllRemoteComponentGroups()
#        self.assertTrue(len(comp_groups) == 1)

    def test_multiple_product_bugtracker(self):
        """Bug tracker with multiple products and varying numbers of components"""
        comp_group_i = self.bugtracker.addRemoteComponentGroup("Product I")

        comp_group_ii = self.bugtracker.addRemoteComponentGroup("Product II")
        comp_group_ii.addComponent("Component II-Alpha")

        comp_group_iii = self.bugtracker.addRemoteComponentGroup("Product III")
        comp_group_iii.addComponent("Component III-Alpha")
        comp_group_iii.addComponent("Component III-Beta")
        comp_group_iii.addComponent("Component III-Gamma")

        comp_group = self.bugtracker.getRemoteComponentGroup('non-existant')
        self.assertEqual(comp_group, None)

        comp_group = self.bugtracker.getRemoteComponentGroup('Product II')
# TODO: Implement
#        self.assertEqual(comp_group, comp_group_ii)

        comp_groups = self.bugtracker.getAllRemoteComponentGroups()
# TODO: Implement
#        self.assertEqual(len(comp_groups), 3)

    def test_get_components_for_component_group(self):
        """Retrieve a set of components from a given product"""

        default_comp_group = self.bugtracker.addRemoteComponentGroup("Default")
        default_comp_group.addComponent("Alpha")
        default_comp_group.addComponent("Beta")
        default_comp_group.addComponent("Gamma")

        comp_group = self.bugtracker.getRemoteComponentGroup('Default')
# TODO: Implement
#        self.assertEqual(len(comp_group.components), 3)

# TODO: Implement
        #comp = comp_group.getComponent('Single Beta')
        #self.assertEqual(comp.name, 'Single Beta')

    def test_link_source_package_to_component(self):
        """Verify a source package can be linked to an upstream component"""

        default_comp_group = self.bugtracker.addRemoteComponentGroup("Default")
        default_comp_group.addComponent("Alpha")

        comp_group = self.bugtracker.getRemoteComponentGroup('Default')
# TODO: Implement
        #comp = comp_group.getComponent('Alpha')
        #self.assertEqual(comp.source_package, None)

# TODO: Implement
        #comp.link_source_package('test-source-package')
        # TODO: Actually, test that it links to the real source package
        #self.assertEqual(comp.source_package, 'test-source-package')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))

    return suite


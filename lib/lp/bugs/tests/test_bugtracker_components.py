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

# TODO: Decide better about how to organize classes for tests
# TODO: Add test for invalid naming and valid_name constraint checking

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
        component = self.factory.makeBugTrackerComponent(
            u'foobar', self.comp_group)
        self.assertTrue(component is not None)

    def test_set_visibility(self):
        component = self.factory.makeBugTrackerComponent(
            u'foobar', self.comp_group)
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
            u'custom-foobar', self.comp_group, custom=True)
        self.assertTrue(custom_component != None)
        self.assertEqual(custom_component.is_custom, True)

    def test_multiple_component_creation(self):
        comp_a = self.factory.makeBugTrackerComponent(
            u'a', self.comp_group)
        comp_b = self.factory.makeBugTrackerComponent(
            u'b', self.comp_group)
        comp_c = self.factory.makeBugTrackerComponent(
            u'c', self.comp_group, True)

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

        comp_groups = self.bug_tracker.getAllRemoteComponentGroups()
        self.assertEqual(len(list(comp_groups)), 0)


    def test_single_product_bugtracker(self):
        """Bug tracker with a single (default) product and several components"""

        default_comp_group = self.bug_tracker.addRemoteComponentGroup(u'single')

#        default_comp_group.addComponent("alpha")
#        default_comp_group.addComponent("beta")
#        default_comp_group.addComponent("gamma")

#        comp_group = self.bug_tracker.getRemoteComponentGroup('non-existant')
#        self.assertEqual(comp_group, None)

#        comp_group = self.bug_tracker.getRemoteComponentGroup(u'single')
#        self.assertEqual(comp_group, default_comp_group)
#        self.assertEqual(comp_group.name, u'single')

        comp_groups = self.bug_tracker.getAllRemoteComponentGroups()
        self.assertEqual(len(list(comp_groups)), 1)

    def test_multiple_product_bugtracker(self):
        """Bug tracker with multiple products and varying numbers of components"""
        comp_group_i = self.bug_tracker.addRemoteComponentGroup(u'product1')

#        comp_group_ii = self.bugtracker.addRemoteComponentGroup(u'product2')
#        comp_group_ii.addComponent(u'component2-alpha')

#        comp_group_iii = self.bugtracker.addRemoteComponentGroup(u'product3')
#        comp_group_iii.addComponent(u'component3-alpha')
#        comp_group_iii.addComponent(u'component3-beta')
#        comp_group_iii.addComponent(u'component3-gamma')

#        comp_group = self.bugtracker.getRemoteComponentGroup(u'non-existant')
#        self.assertEqual(comp_group, None)

#        comp_group = self.bugtracker.getRemoteComponentGroup(u'product2')
#        self.assertEqual(comp_group, comp_group_ii)

#        comp_groups = self.bugtracker.getAllRemoteComponentGroups()
#        self.assertEqual(len(list(comp_groups)), 3)

    def test_get_components_for_component_group(self):
        """Retrieve a set of components from a given product"""

#        default_comp_group = self.bugtracker.addRemoteComponentGroup(u'default')
#        default_comp_group.addComponent(u'alpha')
#        default_comp_group.addComponent(u'beta')
#        default_comp_group.addComponent(u'gamma')

#        comp_group = self.bugtracker.getRemoteComponentGroup(u'default')
#        self.assertEqual(len(list(comp_group.components)), 3)

        #comp = comp_group.getComponent(u'beta')
        #self.assertEqual(comp.name, u'beta')

    def test_link_source_package_to_component(self):
        """Verify a source package can be linked to an upstream component"""

#        default_comp_group = self.bugtracker.addRemoteComponentGroup(u'default')
#        default_comp_group.addComponent(u'alpha')

#        comp_group = self.bugtracker.getRemoteComponentGroup(u'default')
        #comp = comp_group.getComponent(u'alpha')
        #self.assertEqual(comp.source_package, None)

        #comp.link_source_package(u'test-source-package')
        # TODO: Actually, test that it links to the real source package
        #self.assertEqual(comp.source_package, u'test-source-package')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))

    return suite


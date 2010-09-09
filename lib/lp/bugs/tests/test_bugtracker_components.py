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

    def test_component_creation(self):
        component = self.factory.makeBugTrackerComponent("Foobar")
        self.assertTrue(component != None)

    def test_set_visibility(self):
        component = self.factory.makeBugTrackerComponent("Foobar")
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
            "CustomComponent", custom=True)
        self.assertTrue(custom_component != None)
        self.assertEqual(custom_component.is_custom, True)

    def test_multiple_components(self):
        comp_group = self.factory.makeBugTrackerComponentGroup()
        
        comp_a = self.factory.makeBugTrackerComponent("a", comp_group)
        comp_b = self.factory.makeBugTrackerComponent("b", comp_group)
        comp_c = self.factory.makeBugTrackerComponent("c", comp_group, True)

        self.assertTrue(comp_a != None)
        self.assertTrue(comp_b != None)
        self.assertTrue(comp_c != None)


class TestBugTrackerWithComponents(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    empty_bt = None
    single_product_bt = None
    multi_product_bt = None

    def setUp(self):
        login(ANONYMOUS)
        super(TestBugTrackerWithComponents, self).setUp()

        self.empty_bt = self.factory.makeBugTracker()
        self.single_product_bt = self.factory.makeBugTracker()
        self.multi_product_bt = self.factory.makeBugTracker()

        self.single_product_bt.addRemoteComponentGroup("Single")
        #self.single_product_bt.addRemoteComponent("Single", "Single Alpha")
        #self.single_product_bt.addRemoteComponent("Single", "Single Beta")
        #self.single_product_bt.addRemoteComponent("Single", "Single Gamma")

        self.multi_product_bt.addRemoteComponentGroup("Product I")
        #self.multi_product_bt.addRemoteComponentGroup("Product II")
        #self.multi_product_bt.addRemoteComponentGroup("Product III")

        #self.multi_product_bt.addRemoteComponent("Product II",  "Component II-Alpha")

        #self.multi_product_bt.addRemoteComponent("Product III", "Component III-Alpha")
        #self.multi_product_bt.addRemoteComponent("Product III", "Component III-Beta")
        #self.multi_product_bt.addRemoteComponent("Product III", "Component III-Gamma")

    def test_get_component_for_distro_source_package(self):
        """Given a source package, find out what bugzilla component it maps to"""

        # An empty bug tracker has no components
        #comp = self.empty_bt.componentForDistroSourcePackage('non-existant-source-package')
        #self.assertEqual(comp, None)

        # We should be able to directly retrieve the component from
        # bug trackers that don't organize by product type
        #comp = self.single_product_bt.componentForDistroSourcePackage(source_package_name)
        #self.assertEqual(comp.name, 'Single Beta')

    def test_get_all_component_groups_for_externalbugtracker(self):
        """Retrieve the products list from the external bug tracker

        Verify that it returns the appropriate quantity of products
        (aka component groups)
        """
        comp_groups = self.empty_bt.getAllRemoteComponentGroups()
        self.assertTrue(len(comp_groups) == 0)

        comp_groups = self.single_product_bt.getAllRemoteComponentGroups()
        #TODO
        #self.assertTrue(len(comp_groups) == 1)

        comp_groups = self.multi_product_bt.getAllRemoteComponentGroups()
        #TODO
        #self.assertTrue(len(comp_groups) > 1)

    
    def test_get_component_group_from_externalbugtracker(self):
        """Retrieve the products list from the external bug tracker"""

        comp_group = self.empty_bt.getRemoteComponentGroup('non-existant')
        self.assertEqual(comp_group, None)

        comp_group = self.single_product_bt.getRemoteComponentGroup('Single')
        #TODO
        #self.assertEqual(comp_group.name, "Single")

        comp_group = self.multi_product_bt.getRemoteComponentGroup('Product II')
        #TODO
        #self.assertEqual(comp_group.name, "Product II")

    def test_get_components_for_component_group(self):
        """Retrieve a set of components from a given product"""

        #comp_group = self.single_product_bt.getRemoteComponentGroup('Single')
        #self.assertTrue(len(comp_group.components) > 1)

        #comp = comp_group.getComponent('Single Beta')
        #self.assertEqual(comp.name, 'Single Beta')
        
    def test_link_source_package_to_component(self):
        """Verify a source package can be linked to an upstream component"""

        #comp_group = self.single_product_bt.getRemoteComponentGroup('Single')
        #comp = comp_group.getComponent('Single Beta')
        #self.assertEqual(comp.source_package, None)

        #comp.link_source_package('test-source-package')
        # TODO: Actually, test that it links to the real source package
        #self.assertEqual(comp.source_package, 'test-source-package')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))

    return suite


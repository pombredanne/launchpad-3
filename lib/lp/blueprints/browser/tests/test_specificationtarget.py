# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.blueprints.interfaces.specificationtarget import (
    IHasSpecifications,
    ISpecificationTarget,
    )
from lp.app.enums import ServiceUsage
from lp.blueprints.publisher import BlueprintsLayer
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import (
    create_view,
    create_initialized_view,
    )


class TestRegisterABlueprintButtonView(TestCaseWithFactory):
    """Test specification menus links."""
    layer = DatabaseFunctionalLayer

    def verify_view(self, context, name):
        view = create_view(
            context, '+register-a-blueprint-button')
        self.assertEqual(
            'http://blueprints.launchpad.dev/%s/+addspec' % name,
            view.target_url)
        self.assertTrue(
            '<div id="involvement" class="portlet involvement">' in view())

    def test_specificationtarget(self):
        context = self.factory.makeProduct(name='almond')
        self.assertTrue(ISpecificationTarget.providedBy(context))
        self.verify_view(context, context.name)

    def test_adaptable_to_specificationtarget(self):
        context = self.factory.makeProject(name='hazelnut')
        self.assertFalse(ISpecificationTarget.providedBy(context))
        self.verify_view(context, context.name)

    def test_sprint(self):
        # Sprints are a special case. They are not ISpecificationTargets,
        # nor can they be adapted to a ISpecificationTarget,
        # but can create a spcification for a ISpecificationTarget.
        context = self.factory.makeSprint(title='Walnut', name='walnut')
        self.assertFalse(ISpecificationTarget.providedBy(context))
        self.verify_view(context, 'sprints/%s' % context.name)


class TestHasSpecificationsViewInvolvement(TestCaseWithFactory):
    """Test specification menus links."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.user = self.factory.makePerson(name="macadamia")
        login_person(self.user)

    def verify_involvment(self, context):
        self.assertTrue(IHasSpecifications.providedBy(context))
        view = create_view(
            context, '+specs', layer=BlueprintsLayer, principal=self.user)
        self.assertTrue(
            '<div id="involvement" class="portlet involvement">' in view())

    def test_specificationtarget(self):
        context = self.factory.makeProduct(name='almond')
        naked_product = removeSecurityProxy(context)
        naked_product.blueprints_usage = ServiceUsage.LAUNCHPAD
        self.verify_involvment(context)

    def test_adaptable_to_specificationtarget(self):
        context = self.factory.makeProject(name='hazelnut')
        self.verify_involvment(context)

    def test_sprint(self):
        context = self.factory.makeSprint(title='Walnut', name='walnut')
        self.verify_involvment(context)

    def test_person(self):
        context = self.factory.makePerson(name='pistachio')
        self.assertTrue(IHasSpecifications.providedBy(context))
        view = create_view(
            context, '+specs', layer=BlueprintsLayer, principal=self.user)
        self.assertFalse(
            '<div id="involvement" class="portlet involvement">' in view())


class TestHasSpecificationsTemplates(TestCaseWithFactory):
    """Tests the selection of templates based on blueprints usage."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestHasSpecificationsTemplates, self).setUp()
        self.user = self.factory.makePerson()
        self.product = self.factory.makeProduct()
        self.naked_product = removeSecurityProxy(self.product)
        login_person(self.user)

    def test_not_configured(self):
        self.naked_product.blueprints_usage = ServiceUsage.UNKNOWN
        view = create_view(
            self.product,
            '+specs',
            layer=BlueprintsLayer,
            principal=self.user)
        self.assertEqual(
            view.not_launchpad_template.filename,
            view.template.filename)

    def test_external(self):
        self.naked_product.blueprints_usage = ServiceUsage.EXTERNAL
        view = create_view(
            self.product,
            '+specs',
            layer=BlueprintsLayer,
            principal=self.user)
        self.assertEqual(
            view.not_launchpad_template.filename,
            view.template.filename)

    def test_not_applicable(self):
        self.naked_product.blueprints_usage = ServiceUsage.NOT_APPLICABLE
        view = create_view(
            self.product,
            '+specs',
            layer=BlueprintsLayer,
            principal=self.user)
        self.assertEqual(
            view.not_launchpad_template.filename,
            view.template.filename)

    def test_on_launchpad(self):
        self.naked_product.blueprints_usage = ServiceUsage.LAUNCHPAD
        view = create_view(
            self.product,
            '+specs',
            layer=BlueprintsLayer,
            principal=self.user)
        self.assertEqual(
            view.default_template.filename,
            view.template.filename)


class TestHasSpecificationsConfiguration(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_cannot_configure_blueprints_product_no_edit_permission(self):
        product = self.factory.makeProduct()
        view = create_initialized_view(product, '+specs')
        self.assertEqual(False, view.can_configure_blueprints)

    def test_can_configure_blueprints_product_with_edit_permission(self):
        product = self.factory.makeProduct()
        login_person(product.owner)
        view = create_initialized_view(product, '+specs')
        self.assertEqual(True, view.can_configure_blueprints)

    def test_cannot_configure_blueprints_distribution_no_edit_permission(self):
        distribution = self.factory.makeDistribution()
        view = create_initialized_view(distribution, '+specs')
        self.assertEqual(False, view.can_configure_blueprints)

    def test_can_configure_blueprints_distribution_with_edit_permission(self):
        distribution = self.factory.makeDistribution()
        login_person(distribution.owner)
        view = create_initialized_view(distribution, '+specs')
        self.assertEqual(True, view.can_configure_blueprints)

    def test_cannot_configure_blueprints_projectgroup_with_edit_permission(self):
        project_group = self.factory.makeProject()
        login_person(project_group.owner)
        view = create_initialized_view(project_group, '+specs')
        self.assertEqual(False, view.can_configure_blueprints)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.blueprints.interfaces.specificationtarget import (
    IHasSpecifications,
    ISpecificationTarget,
    )
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


class TestHasSpecificationsView(TestCaseWithFactory):
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

    def test_specs_batch(self):
        # Some pages turn up in very large contexts and patch. E.g.
        # Distro:+assignments which uses SpecificationAssignmentsView, a
        # subclass.
        person = self.factory.makePerson()
        view = create_initialized_view(person, name='+assignments')
        self.assertIsInstance(view.specs_batched, BatchNavigator)

    def test_batch_headings(self):
        person = self.factory.makePerson()
        view = create_initialized_view(person, name='+assignments')
        navigator = view.specs_batched
        self.assertEqual('specification', navigator._singular_heading)
        self.assertEqual('specifications', navigator._plural_heading)

    def test_batch_size(self):
        # Because +assignments is meant to provide an overview, we default to
        # 500 as the default batch size.
        person = self.factory.makePerson()
        view = create_initialized_view(person, name='+assignments')
        navigator = view.specs_batched
        self.assertEqual(500, view.specs_batched.default_size)


class TestAssignments(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_assignments_are_batched(self):
        product = self.factory.makeProduct()
        spec1 = self.factory.makeSpecification(product=product)
        spec2 = self.factory.makeSpecification(product=product)
        view = create_initialized_view(product, name='+assignments',
            query_string="batch=1")
        content = view.render()
        self.assertEqual('next',
            find_tag_by_id(content, 'upper-batch-nav-batchnav-next')['class'])
        self.assertEqual('next',
            find_tag_by_id(content, 'lower-batch-nav-batchnav-next')['class'])
        

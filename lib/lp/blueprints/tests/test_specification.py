# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for Specification."""

__metaclass__ = type

from textwrap import dedent

from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.blueprints.enums import (
    NewSpecificationDefinitionStatus,
    SpecificationDefinitionStatus,
    SpecificationGoalStatus,
    )
from lp.blueprints.errors import TargetAlreadyHasSpecification
from lp.blueprints.interfaces.specification import ISpecificationSet
from lp.blueprints.model.specification import (
    extractWorkItemsFromWhiteboard,
    SpecificationWorkItemStatus,
    WorkitemParser,
    )
from lp.services.webapp.authorization import check_permission
from lp.testing import (
    login_person,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class SpecificationTests(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_target_driver_has_edit_rights(self):
        """Drivers of a blueprint's target can edit that blueprint."""
        product = self.factory.makeProduct()
        driver = self.factory.makePerson()
        removeSecurityProxy(product).driver = driver
        specification = self.factory.makeSpecification(product=product)
        login_person(driver)
        self.assertTrue(check_permission('launchpad.Edit', specification))

    def test_auto_accept_of_goal_for_drivers(self):
        """Drivers of a series accept the goal when they propose."""
        product = self.factory.makeProduct()
        proposer = self.factory.makePerson()
        productseries = self.factory.makeProductSeries(product=product)
        removeSecurityProxy(productseries).driver = proposer
        specification = self.factory.makeSpecification(product=product)
        specification.proposeGoal(productseries, proposer)
        self.assertEqual(
            SpecificationGoalStatus.ACCEPTED, specification.goalstatus)

    def test_goal_not_accepted_for_non_drivers(self):
        """People who aren't drivers don't have their proposals approved."""
        product = self.factory.makeProduct()
        proposer = self.factory.makePerson()
        productseries = self.factory.makeProductSeries(product=product)
        specification = self.factory.makeSpecification(product=product)
        specification.proposeGoal(productseries, proposer)
        self.assertEqual(
            SpecificationGoalStatus.PROPOSED, specification.goalstatus)

    def test_retarget_existing_specification(self):
        """An error is raised if the name is already taken."""
        product1 = self.factory.makeProduct()
        product2 = self.factory.makeProduct()
        specification1 = self.factory.makeSpecification(
            product=product1, name="foo")
        self.factory.makeSpecification(product=product2, name="foo")
        self.assertRaises(
            TargetAlreadyHasSpecification,
            removeSecurityProxy(specification1).retarget, product2)

    def test_retarget_is_protected(self):
        specification = self.factory.makeSpecification(
            product=self.factory.makeProduct())
        self.assertRaises(
            Unauthorized, getattr, specification, 'retarget')

    def test_validate_move_existing_specification(self):
        """An error is raised by validateMove if the name is already taken."""
        product1 = self.factory.makeProduct()
        product2 = self.factory.makeProduct()
        specification1 = self.factory.makeSpecification(
            product=product1, name="foo")
        self.factory.makeSpecification(
            product=product2, name="foo")
        self.assertRaises(
            TargetAlreadyHasSpecification, specification1.validateMove,
            product2)

    def test_setTarget(self):
        product = self.factory.makeProduct()
        specification = self.factory.makeSpecification(product=product)
        self.assertEqual(product, specification.target)
        self.assertIs(None, specification.distribution)

        distribution = self.factory.makeDistribution()
        removeSecurityProxy(specification).setTarget(distribution)

        self.assertEqual(distribution, specification.target)
        self.assertEqual(distribution, specification.distribution)
        self.assertIs(None, specification.product)

    def test_setTarget_is_protected(self):
        specification = self.factory.makeSpecification(
            product=self.factory.makeProduct())
        self.assertRaises(
            Unauthorized, getattr, specification, 'setTarget')


class TestSpecificationSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSpecificationSet, self).setUp()
        self.specification_set = getUtility(ISpecificationSet)
        self.new_names = NewSpecificationDefinitionStatus.items.mapping.keys()

    def test_new_with_open_definition_status_creates_specification(self):
        # Calling new() with an open definition status will will create
        # a specification.
        self.assertTrue(
            SpecificationDefinitionStatus.NEW.name in self.new_names)
        product = self.factory.makeProduct()
        spec = self.specification_set.new(
            name='plane', title='Place', specurl='http://eg.org/plane',
            summary='summary', owner=product.owner, product=product,
            definition_status=SpecificationDefinitionStatus.NEW)
        self.assertEqual(
            SpecificationDefinitionStatus.NEW, spec.definition_status)

    def test_new_with_closed_definition_status_raises_error(self):
        # Calling new() with a obsolete or superseded definition status
        # raises an error.
        self.assertTrue(
            SpecificationDefinitionStatus.OBSOLETE.name not in self.new_names)
        product = self.factory.makeProduct()
        args = dict(
            name='plane', title='Place', specurl='http://eg.org/plane',
            summary='summary', owner=product.owner, product=product,
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        self.assertRaises(
            AssertionError, self.specification_set.new, **args)


class FakeSpecification(object):
    assignee = None


# This test doesn't need to use the database, so we can keep it without a
# layer and that will make it run much faster than the other.
class TestWorkItemParser(TestCase):

    def test_parse_line_basic(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "A single work item: TODO")
        self.assertEqual(
            [None, "A single work item", SpecificationWorkItemStatus.TODO],
            [assignee, description, status])

    def test_parse_line_with_assignee(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "[salgado] A single work item: TODO")
        self.assertEqual(
            ["salgado", "A single work item",
             SpecificationWorkItemStatus.TODO],
            [assignee, description, status])

    def test_parse_line_without_status(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "A single work item")
        self.assertEqual(
            [None, "A single work item", SpecificationWorkItemStatus.TODO],
            [assignee, description, status])

    def test_parse_empty_line(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem("")
        self.assertEqual(
            [None, "A single work item", SpecificationWorkItemStatus.TODO],
            [assignee, description, status])



class TestSpecificationWorkItemExtractionFromWhiteboard(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_None_whiteboard(self):
        spec = self.factory.makeSpecification(whiteboard=None)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual([], work_items)

    def test_empty_whiteboard(self):
        spec = self.factory.makeSpecification(whiteboard='')
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual([], work_items)

    def test_single_work_item(self):
        whiteboard = dedent("""
            Work items:
            A single work item: TODO
            """)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(
            [(None, u'A single work item', SpecificationWorkItemStatus.TODO,
              None)],
            work_items)

    def test_multiple_work_items(self):
        whiteboard = dedent("""
            Work items:
            A single work item: TODO
            Another work item: DONE
            """)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(
            [(None, 'A single work item', SpecificationWorkItemStatus.TODO,
              None),
             (None, 'Another work item', SpecificationWorkItemStatus.DONE,
              None)],
            work_items)

    def test_work_item_with_assignee(self):
        person = self.factory.makePerson()
        whiteboard = dedent("""
            Work items for:
            [%s] A single work item: TODO
            """ % person.name)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(
            [(person.name, 'A single work item',
              SpecificationWorkItemStatus.TODO, None)],
            work_items)

    def test_work_item_with_milestone(self):
        milestone = self.factory.makeMilestone()
        whiteboard = dedent("""
            Work items for %s:
            A single work item: TODO
            """ % milestone.name)
        spec = self.factory.makeSpecification(
            whiteboard=whiteboard, product=milestone.product)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(
            [(None, u'A single work item', SpecificationWorkItemStatus.TODO,
              milestone.name)],
            work_items)

    def test_whiteboard_with_all_possible_sections(self):
        whiteboard = dedent("""
            Work items:
            A single work item: TODO

            Meta:
            Headline: Foo bar
            Acceptance: Baz foo

            Complexity:
            [user1] milestone1: 10
            """)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(
            [(None, "A single work item", SpecificationWorkItemStatus.TODO,
              None)],
            work_items)

        # Now assert that the work items were removed from the whiteboard.
        self.assertEqual(dedent("""
            Meta:
            Headline: Foo bar
            Acceptance: Baz foo

            Complexity:
            [user1] milestone1: 10
            """).strip(), spec.whiteboard.strip())

    def test_error_when_parsing(self):
        """If there's an error when parsing the whiteboard, we leave it
        unchanged and do not create any SpecificationWorkItem objects."""
        self.fail('TODO')

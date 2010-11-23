# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from canonical.testing.layers import DatabaseFunctionalLayer
from lp.blueprints.errors import TargetAlreadyHasSpecification
from lp.blueprints.interfaces.specification import SpecificationGoalStatus
from lp.testing import TestCaseWithFactory


class SpecificationTests(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_auto_accept_of_goal_for_drivers(self):
        """Drivers of a series accept the goal when they propose."""
        product = self.factory.makeProduct()
        proposer = self.factory.makePerson()
        productseries = self.factory.makeProductSeries(product=product)
        productseries.driver = proposer
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
        specification2 = self.factory.makeSpecification(
            product=product2, name="foo")
        self.assertRaises(
            TargetAlreadyHasSpecification, specification1.retarget,
            product=product2)

    def test_validate_move_existing_specification(self):
        """An error is raised by validateMove if the name is already taken."""
        product1 = self.factory.makeProduct()
        product2 = self.factory.makeProduct()
        specification1 = self.factory.makeSpecification(
            product=product1, name="foo")
        specification2 = self.factory.makeSpecification(
            product=product2, name="foo")
        self.assertRaises(
            TargetAlreadyHasSpecification, specification1.validateMove,
            product2)

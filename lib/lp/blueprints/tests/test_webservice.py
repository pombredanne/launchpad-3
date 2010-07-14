# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad blueprints."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.testing.pages import webservice_for_person
from lp.blueprints.interfaces.specification import (
    SpecificationDefinitionStatus, SpecificationGoalStatus,
    SpecificationPriority)
from lp.testing import (
    launchpadlib_for, TestCaseWithFactory)


class SpecificationAttributeWebserviceTests(TestCaseWithFactory):
    """Test accessing specification attributes over the webservice."""
    layer = DatabaseFunctionalLayer

    def makeSimpleSpecification(self):
        self.name = "some-spec"
        self.title = "some-title"
        self.url = "http://example.org/some_url"
        self.summary = "Some summary."
        definition_status = SpecificationDefinitionStatus.PENDINGAPPROVAL
        self.definition_status = definition_status.title
        self.assignee_name = "james-w"
        assignee = self.factory.makePerson(name=self.assignee_name)
        self.drafter_name = "jml"
        drafter = self.factory.makePerson(name=self.drafter_name)
        self.approver_name = "bob"
        approver = self.factory.makePerson(name=self.approver_name)
        self.owner_name = "mary"
        owner = self.factory.makePerson(name=self.owner_name)
        priority = SpecificationPriority.HIGH
        self.priority = priority.title
        goal_status = SpecificationGoalStatus.PROPOSED
        self.goal_status = goal_status.title
        self.whiteboard = "Some whiteboard"
        product = self.factory.makeProduct()
        return self.factory.makeSpecification(
            product=product, name=self.name,
            title=self.title, specurl=self.url,
            summary=self.summary,
            definition_status=definition_status,
            assignee=assignee, drafter=drafter, approver=approver,
            priority=priority,
            owner=owner, whiteboard=self.whiteboard, goalstatus=goal_status)

    def makeProduct(self):
        return self.factory.makeProduct(name="fooix")

    def getResponse(self, spec_object):
        user = self.factory.makePerson()
        launchpadlib = launchpadlib_for(
            "testing", user)
        return launchpadlib.load(
            str(launchpadlib._root_uri) + '/%s/+spec/%s'
            % (spec_object.product.name, spec_object.name))

    def getSimpleSpecificationResponse(self):
        self.spec_object = self.makeSimpleSpecification()
        return self.getResponse(self.spec_object)

    def test_can_retrieve_representation(self):
        spec = self.makeSimpleSpecification()
        user = self.factory.makePerson()
        webservice = webservice_for_person(user)
        response = webservice.get(
            '/%s/+spec/%s' % (spec.product.name, spec.name))
        self.assertEqual(response.status, 200)

    def test_representation_contains_name(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.name, spec.name)

    def test_representation_contains_title(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.title, spec.title)

    def test_representation_contains_specification_url(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.url, spec.specification_url)

    def test_representation_contains_summary(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.summary, spec.summary)

    def test_representation_contains_definition_status(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(
            self.definition_status, spec.definition_status)

    def test_representation_contains_assignee(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.assignee_name, spec.assignee.name)

    def test_representation_contains_drafter(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.drafter_name, spec.drafter.name)

    def test_representation_contains_approver(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.approver_name, spec.approver.name)

    def test_representation_contains_owner(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.owner_name, spec.owner.name)

    def test_representation_contains_priority(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.priority, spec.priority)

    def test_representation_contains_date_created(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.spec_object.datecreated, spec.date_created)

    def test_representation_contains_goal_status(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.goal_status, spec.goal_status)

    def test_representation_contains_whiteboard(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.whiteboard, spec.whiteboard)

    def test_representation_with_no_whiteboard(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, whiteboard=None)
        # Check that the factory didn't add a whiteboard
        self.assertEqual(None, spec_object.whiteboard)
        spec = self.getResponse(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.whiteboard)

    def test_representation_with_no_approver(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, approver=None)
        # Check that the factory didn't add an approver
        self.assertEqual(None, spec_object.approver)
        spec = self.getResponse(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.approver)

    def test_representation_with_no_drafter(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, drafter=None)
        # Check that the factory didn't add an drafter
        self.assertEqual(None, spec_object.drafter)
        spec = self.getResponse(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.drafter)

    def test_representation_with_no_assignee(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, assignee=None)
        # Check that the factory didn't add an assignee
        self.assertEqual(None, spec_object.assignee)
        spec = self.getResponse(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.assignee)

    def test_representation_with_no_specification_url(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, specurl=None)
        # Check that the factory didn't add an specurl
        self.assertEqual(None, spec_object.specurl)
        spec = self.getResponse(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.specification_url)


# TODO: product, distribution, etc.

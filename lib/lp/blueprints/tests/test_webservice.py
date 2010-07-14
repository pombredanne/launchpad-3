# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad blueprints."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.testing.pages import webservice_for_person
from lp.blueprints.interfaces.specification import (
    SpecificationDefinitionStatus)
from lp.testing import (
    launchpadlib_for, TestCaseWithFactory)


class SpecificationWebserviceTests(TestCaseWithFactory):
    """Test interacting with the specifications webservice."""
    layer = DatabaseFunctionalLayer

    def makeSimpleSpecification(self):
        self.simple_name = "some-spec"
        self.simple_title = "some-title"
        self.simple_url = "http://example.org/some_url"
        self.simple_summary = "Some summary."
        definition_status = SpecificationDefinitionStatus.PENDINGAPPROVAL
        self.simple_definition_status = definition_status.title
        product = self.factory.makeProduct(name="fooix")
        return self.factory.makeSpecification(
            product=product, name=self.simple_name,
            title=self.simple_title, specurl=self.simple_url,
            summary=self.simple_summary,
            definition_status=definition_status)

    def getSimpleSpecificationResponse(self):
        spec = self.makeSimpleSpecification()
        user = self.factory.makePerson()
        launchpadlib = launchpadlib_for(
            "testing", user)
        return launchpadlib.load(
            str(launchpadlib._root_uri) + '/%s/+spec/%s' % (spec.product.name, spec.name))

    def test_can_retrieve_representation(self):
        spec = self.makeSimpleSpecification()
        user = self.factory.makePerson()
        webservice = webservice_for_person(user)
        response = webservice.get(
            '/%s/+spec/%s' % (spec.product.name, spec.name))
        self.assertEqual(response.status, 200)

    def test_representation_contains_name(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.simple_name, spec.name)

    def test_representation_contains_title(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.simple_title, spec.title)

    def test_representation_contains_specification_url(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.simple_url, spec.specification_url)

    def test_representation_contains_summary(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.simple_summary, spec.summary)

    def test_represntation_contains_definition_status(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(
            self.simple_definition_status, spec.definition_status)

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


class SpecificationWebserviceTestCase(TestCaseWithFactory):

    def makeProduct(self):
        return self.factory.makeProduct(name="fooix")

    def makeDistribution(self):
        return self.factory.makeDistribution(name="foobuntu")

    def getLaunchpadlib(self):
        user = self.factory.makePerson()
        return launchpadlib_for("testing", user)

    def getSpecOnWebservice(self, spec_object):
        launchpadlib = self.getLaunchpadlib()
        if spec_object.product is not None:
            pillar_name = spec_object.product.name
        else:
            pillar_name = spec_object.distribution.name
        return launchpadlib.load(
            str(launchpadlib._root_uri) + '/%s/+spec/%s'
            % (pillar_name, spec_object.name))

    def getPillarOnWebservice(self, pillar_obj):
        launchpadlib = self.getLaunchpadlib()
        return launchpadlib.load(
            str(launchpadlib._root_uri) + '/' + pillar_obj.name)


class SpecificationAttributeWebserviceTests(SpecificationWebserviceTestCase):
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

    def getSimpleSpecificationResponse(self):
        self.spec_object = self.makeSimpleSpecification()
        return self.getSpecOnWebservice(self.spec_object)

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
        spec = self.getSpecOnWebservice(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.whiteboard)

    def test_representation_with_no_approver(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, approver=None)
        # Check that the factory didn't add an approver
        self.assertEqual(None, spec_object.approver)
        spec = self.getSpecOnWebservice(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.approver)

    def test_representation_with_no_drafter(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, drafter=None)
        # Check that the factory didn't add an drafter
        self.assertEqual(None, spec_object.drafter)
        spec = self.getSpecOnWebservice(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.drafter)

    def test_representation_with_no_assignee(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, assignee=None)
        # Check that the factory didn't add an assignee
        self.assertEqual(None, spec_object.assignee)
        spec = self.getSpecOnWebservice(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.assignee)

    def test_representation_with_no_specification_url(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, specurl=None)
        # Check that the factory didn't add an specurl
        self.assertEqual(None, spec_object.specurl)
        spec = self.getSpecOnWebservice(spec_object)
        # Check that it is None on the webservice too
        self.assertEqual(None, spec.specification_url)

    def test_representation_has_project_link(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual('fooix', spec.project.name)

    def test_representation_has_project_series_link(self):
        product = self.makeProduct()
        productseries = self.factory.makeProductSeries(
            name='fooix-dev', product=product)
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name, productseries=productseries)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual('fooix-dev', spec.project_series.name)

    def test_representation_has_distribution_link(self):
        distribution = self.makeDistribution()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            distribution=distribution, name=name)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual('foobuntu', spec.distribution.name)

    def test_representation_has_distroseries_link(self):
        distribution = self.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            name='maudlin', distribution=distribution)
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            distribution=distribution, name=name, distroseries=distroseries)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual('maudlin', spec.distroseries.name)

    def test_representation_empty_distribution(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name)
        # Check that we didn't pick one up in the factory
        self.assertEqual(None, spec_object.distribution)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual(None, spec.distribution)

    def test_representation_empty_project_series(self):
        product = self.makeProduct()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            product=product, name=name)
        # Check that we didn't pick one up in the factory
        self.assertEqual(None, spec_object.productseries)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual(None, spec.project_series)

    def test_representation_empty_project(self):
        distribution = self.makeDistribution()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            distribution=distribution, name=name)
        # Check that we didn't pick one up in the factory
        self.assertEqual(None, spec_object.product)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual(None, spec.project)

    def test_representation_empty_distroseries(self):
        distribution = self.makeDistribution()
        name = "some-spec"
        spec_object = self.factory.makeSpecification(
            distribution=distribution, name=name)
        # Check that we didn't pick one up in the factory
        self.assertEqual(None, spec_object.distroseries)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual(None, spec.distroseries)

    def test_representation_contains_milestone(self):
        product = self.makeProduct()
        productseries = self.factory.makeProductSeries(product=product)
        milestone = self.factory.makeMilestone(
            name="1.0", product=product, productseries=productseries)
        spec_object = self.factory.makeSpecification(
            product=product, productseries=productseries, milestone=milestone)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual("1.0", spec.milestone.name)

    def test_representation_empty_milestone(self):
        product = self.makeProduct()
        spec_object = self.factory.makeSpecification(
            product=product, milestone=None)
        # Check that the factory didn't add a milestone
        self.assertEqual(None, spec_object.milestone)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual(None, spec.milestone)


class SpecificationTargetTests(SpecificationWebserviceTestCase):
    """Tests for accessing specifications via their targets."""
    layer = DatabaseFunctionalLayer

    def test_get_specification_on_product(self):
        product = self.makeProduct()
        spec_object = self.factory.makeSpecification(
            product=product, name="some-spec")
        product_on_webservice = self.getPillarOnWebservice(product)
        spec = product_on_webservice.getSpecification(name="some-spec")
        self.assertEqual("some-spec", spec.name)
        self.assertEqual("fooix", spec.project.name)

    def test_get_specification_not_found(self):
        product = self.makeProduct()
        product_on_webservice = self.getPillarOnWebservice(product)
        spec = product_on_webservice.getSpecification(name="nonexistant")
        self.assertEqual(None, spec)

    def test_get_specification_on_distribution(self):
        distribution = self.makeDistribution()
        spec_object = self.factory.makeSpecification(
            distribution=distribution, name="some-spec")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        spec = distro_on_webservice.getSpecification(name="some-spec")
        self.assertEqual("some-spec", spec.name)
        self.assertEqual("foobuntu", spec.distribution.name)

    def test_get_specification_on_productseries(self):
        product = self.makeProduct()
        productseries = self.factory.makeProductSeries(
            product=product, name="fooix-dev")
        spec_object = self.factory.makeSpecification(
            product=product, name="some-spec", productseries=productseries)
        product_on_webservice = self.getPillarOnWebservice(product)
        productseries_on_webservice = product_on_webservice.getSeries(
            name="fooix-dev")
        spec = productseries_on_webservice.getSpecification(name="some-spec")
        self.assertEqual("some-spec", spec.name)
        self.assertEqual("fooix", spec.project.name)
        self.assertEqual("fooix-dev", spec.project_series.name)

    def test_get_specification_on_distroseries(self):
        distribution = self.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution, name="maudlin")
        spec_object = self.factory.makeSpecification(
            distribution=distribution, name="some-spec",
            distroseries=distroseries)
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        distroseries_on_webservice = distro_on_webservice.getSeries(
            name_or_version="maudlin")
        spec = distroseries_on_webservice.getSpecification(name="some-spec")
        self.assertEqual("some-spec", spec.name)
        self.assertEqual("foobuntu", spec.distribution.name)
        self.assertEqual("maudlin", spec.distroseries.name)


class IHasSpecificationsTests(SpecificationWebserviceTestCase):
    """Tests for accessing IHasSpecifications methods over the webservice."""
    layer = DatabaseFunctionalLayer

    def assertNamesOfSpecificationsAre(self, names, specifications):
        self.assertEqual(names, [s.name for s in specifications])

    def test_product_getAllSpecifications(self):
        product = self.makeProduct()
        self.factory.makeSpecification(product=product, name="spec1")
        self.factory.makeSpecification(product=product, name="spec2")
        product_on_webservice = self.getPillarOnWebservice(product)
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], product_on_webservice.getAllSpecifications())

    def test_product_getValidSpecifications(self):
        product = self.makeProduct()
        self.factory.makeSpecification(product=product, name="spec1")
        self.factory.makeSpecification(
            product=product, name="spec2",
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        product_on_webservice = self.getPillarOnWebservice(product)
        self.assertNamesOfSpecificationsAre(
            ["spec1"], product_on_webservice.getValidSpecifications())

    def test_distribution_getAllSpecifications(self):
        distribution = self.makeDistribution()
        self.factory.makeSpecification(
            distribution=distribution, name="spec1")
        self.factory.makeSpecification(
            distribution=distribution, name="spec2")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], distro_on_webservice.getAllSpecifications())

    def test_distribution_getValidSpecifications(self):
        distribution = self.makeDistribution()
        self.factory.makeSpecification(
            distribution=distribution, name="spec1")
        self.factory.makeSpecification(
            distribution=distribution, name="spec2",
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        self.assertNamesOfSpecificationsAre(
            ["spec1"], distro_on_webservice.getValidSpecifications())

    def test_distroseries_getAllSpecifications(self):
        distribution = self.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            name='maudlin', distribution=distribution)
        self.factory.makeSpecification(
            distribution=distribution, name="spec1",
            distroseries=distroseries)
        self.factory.makeSpecification(
            distribution=distribution, name="spec2",
            distroseries=distroseries)
        self.factory.makeSpecification(
            distribution=distribution, name="spec3")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        distroseries_on_webservice = distro_on_webservice.getSeries(
            name_or_version="maudlin")
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"],
            distroseries_on_webservice.getAllSpecifications())

    def test_distroseries_getValidSpecifications(self):
        distribution = self.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            name='maudlin', distribution=distribution)
        self.factory.makeSpecification(
            distribution=distribution, name="spec1",
            distroseries=distroseries,
            goalstatus=SpecificationGoalStatus.ACCEPTED)
        self.factory.makeSpecification(
            distribution=distribution, name="spec2",
            goalstatus=SpecificationGoalStatus.DECLINED,
            distroseries=distroseries)
        self.factory.makeSpecification(
            distribution=distribution, name="spec3",
            distroseries=distroseries,
            goalstatus=SpecificationGoalStatus.ACCEPTED,
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            distribution=distribution, name="spec4")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        distroseries_on_webservice = distro_on_webservice.getSeries(
            name_or_version="maudlin")
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec3"],
            distroseries_on_webservice.getValidSpecifications())

    def test_productseries_getAllSpecifications(self):
        product = self.makeProduct()
        productseries = self.factory.makeProductSeries(
            product=product, name="fooix-dev")
        self.factory.makeSpecification(
            product=product, name="spec1", productseries=productseries)
        self.factory.makeSpecification(
            product=product, name="spec2", productseries=productseries)
        self.factory.makeSpecification(product=product, name="spec3")
        product_on_webservice = self.getPillarOnWebservice(product)
        series_on_webservice = product_on_webservice.getSeries(
            name="fooix-dev")
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], series_on_webservice.getAllSpecifications())

    def test_productseries_getValidSpecifications(self):
        product = self.makeProduct()
        productseries = self.factory.makeProductSeries(
            product=product, name="fooix-dev")
        self.factory.makeSpecification(
            product=product, name="spec1", productseries=productseries,
            goalstatus=SpecificationGoalStatus.ACCEPTED)
        self.factory.makeSpecification(
            goalstatus=SpecificationGoalStatus.DECLINED,
            product=product, name="spec2", productseries=productseries)
        self.factory.makeSpecification(
            product=product, name="spec3", productseries=productseries,
            goalstatus=SpecificationGoalStatus.ACCEPTED,
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(product=product, name="spec4")
        product_on_webservice = self.getPillarOnWebservice(product)
        series_on_webservice = product_on_webservice.getSeries(
            name="fooix-dev")
        # Should this be different to the results for distroseries?
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2", "spec3"],
            series_on_webservice.getAllSpecifications())

    def test_projectgroup_getAllSpecifications(self):
        productgroup = self.factory.makeProject()
        other_productgroup = self.factory.makeProject()
        product1 = self.factory.makeProduct(project=productgroup)
        product2 = self.factory.makeProduct(project=productgroup)
        product3 = self.factory.makeProduct(project=other_productgroup)
        self.factory.makeSpecification(
            product=product1, name="spec1")
        self.factory.makeSpecification(
            product=product2, name="spec2",
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            product=product3, name="spec3")
        product_on_webservice = self.getPillarOnWebservice(productgroup)
        # Should this be different to the results for distroseries?
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"],
            product_on_webservice.getAllSpecifications())

    def test_projectgroup_getValidSpecifications(self):
        productgroup = self.factory.makeProject()
        other_productgroup = self.factory.makeProject()
        product1 = self.factory.makeProduct(project=productgroup)
        product2 = self.factory.makeProduct(project=productgroup)
        product3 = self.factory.makeProduct(project=other_productgroup)
        self.factory.makeSpecification(
            product=product1, name="spec1")
        self.factory.makeSpecification(
            product=product2, name="spec2",
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            product=product3, name="spec3")
        product_on_webservice = self.getPillarOnWebservice(productgroup)
        # Should this be different to the results for distroseries?
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"],
            product_on_webservice.getValidSpecifications())

    def test_person_getAllSpecifications(self):
        person = self.factory.makePerson(name="james-w")
        product = self.factory.makeProduct()
        self.factory.makeSpecification(
            product=product, name="spec1", drafter=person)
        self.factory.makeSpecification(
            product=product, name="spec2", approver=person,
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            product=product, name="spec3")
        launchpadlib = self.getLaunchpadlib()
        person_on_webservice = launchpadlib.load(
            str(launchpadlib._root_uri) + '/~james-w')
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], person_on_webservice.getAllSpecifications())

    def test_person_getValidSpecifications(self):
        person = self.factory.makePerson(name="james-w")
        product = self.factory.makeProduct()
        self.factory.makeSpecification(
            product=product, name="spec1", drafter=person)
        self.factory.makeSpecification(
            product=product, name="spec2", approver=person,
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            product=product, name="spec3")
        launchpadlib = self.getLaunchpadlib()
        person_on_webservice = launchpadlib.load(
            str(launchpadlib._root_uri) + '/~james-w')
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], person_on_webservice.getAllSpecifications())

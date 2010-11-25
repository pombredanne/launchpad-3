# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad blueprints."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.testing.pages import webservice_for_person
from lp.blueprints.interfaces.specification import (
    SpecificationDefinitionStatus,
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
        return launchpadlib_for("testing", user, version='devel')

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
        status = SpecificationDefinitionStatus.PENDINGAPPROVAL
        self.definition_status = status.title
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
        self.whiteboard = "Some whiteboard"
        self.product = self.factory.makeProduct()
        return self.factory.makeSpecification(
            product=self.product, name=self.name,
            title=self.title, specurl=self.url,
            summary=self.summary,
            status=status,
            assignee=assignee, drafter=drafter, approver=approver,
            priority=priority,
            owner=owner, whiteboard=self.whiteboard)

    def getSimpleSpecificationResponse(self):
        self.spec_object = self.makeSimpleSpecification()
        return self.getSpecOnWebservice(self.spec_object)

    def test_representation_is_empty_on_1_dot_0(self):
        # ISpecification is exposed on the 1.0 version so that they can be
        # linked against branches, but none of its fields is exposed on that
        # version as we expect it to undergo significant refactorings before
        # it's ready for prime time.
        spec = self.makeSimpleSpecification()
        user = self.factory.makePerson()
        webservice = webservice_for_person(user)
        response = webservice.get(
            '/%s/+spec/%s' % (spec.product.name, spec.name))
        expected_keys = sorted(
            [u'self_link', u'http_etag', u'resource_type_link'])
        self.assertEqual(response.status, 200)
        self.assertEqual(sorted(response.jsonBody().keys()), expected_keys)

    def test_representation_contains_name(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.name, spec.name)

    def test_representation_contains_target(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.product.name, spec.target.name)

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

    def test_representation_contains_whiteboard(self):
        spec = self.getSimpleSpecificationResponse()
        self.assertEqual(self.whiteboard, spec.whiteboard)

    def test_representation_contains_milestone(self):
        product = self.makeProduct()
        productseries = self.factory.makeProductSeries(product=product)
        milestone = self.factory.makeMilestone(
            name="1.0", product=product, productseries=productseries)
        spec_object = self.factory.makeSpecification(
            product=product, goal=productseries, milestone=milestone)
        spec = self.getSpecOnWebservice(spec_object)
        self.assertEqual("1.0", spec.milestone.name)


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
        self.assertEqual("fooix", spec.target.name)

    def test_get_specification_on_distribution(self):
        distribution = self.makeDistribution()
        spec_object = self.factory.makeSpecification(
            distribution=distribution, name="some-spec")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        spec = distro_on_webservice.getSpecification(name="some-spec")
        self.assertEqual("some-spec", spec.name)
        self.assertEqual("foobuntu", spec.target.name)

    def test_get_specification_on_productseries(self):
        product = self.makeProduct()
        productseries = self.factory.makeProductSeries(
            product=product, name="fooix-dev")
        spec_object = self.factory.makeSpecification(
            product=product, name="some-spec", goal=productseries)
        product_on_webservice = self.getPillarOnWebservice(product)
        productseries_on_webservice = product_on_webservice.getSeries(
            name="fooix-dev")
        spec = productseries_on_webservice.getSpecification(name="some-spec")
        self.assertEqual("some-spec", spec.name)
        self.assertEqual("fooix", spec.target.name)

    def test_get_specification_on_distroseries(self):
        distribution = self.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution, name="maudlin")
        spec_object = self.factory.makeSpecification(
            distribution=distribution, name="some-spec",
            goal=distroseries)
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        distroseries_on_webservice = distro_on_webservice.getSeries(
            name_or_version="maudlin")
        spec = distroseries_on_webservice.getSpecification(name="some-spec")
        self.assertEqual("some-spec", spec.name)
        self.assertEqual("foobuntu", spec.target.name)

    def test_get_specification_not_found(self):
        product = self.makeProduct()
        product_on_webservice = self.getPillarOnWebservice(product)
        spec = product_on_webservice.getSpecification(name="nonexistant")
        self.assertEqual(None, spec)


class IHasSpecificationsTests(SpecificationWebserviceTestCase):
    """Tests for accessing IHasSpecifications methods over the webservice."""
    layer = DatabaseFunctionalLayer

    def assertNamesOfSpecificationsAre(self, expected_names, specifications):
        names = [s.name for s in specifications]
        self.assertEqual(sorted(expected_names), sorted(names))

    def test_product_all_specifications(self):
        product = self.makeProduct()
        self.factory.makeSpecification(product=product, name="spec1")
        self.factory.makeSpecification(product=product, name="spec2")
        product_on_webservice = self.getPillarOnWebservice(product)
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], product_on_webservice.all_specifications)

    def test_product_valid_specifications(self):
        product = self.makeProduct()
        self.factory.makeSpecification(product=product, name="spec1")
        self.factory.makeSpecification(
            product=product, name="spec2",
            status=SpecificationDefinitionStatus.OBSOLETE)
        product_on_webservice = self.getPillarOnWebservice(product)
        self.assertNamesOfSpecificationsAre(
            ["spec1"], product_on_webservice.valid_specifications)

    def test_distribution_all_specifications(self):
        distribution = self.makeDistribution()
        self.factory.makeSpecification(
            distribution=distribution, name="spec1")
        self.factory.makeSpecification(
            distribution=distribution, name="spec2")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], distro_on_webservice.all_specifications)

    def test_distribution_valid_specifications(self):
        distribution = self.makeDistribution()
        self.factory.makeSpecification(
            distribution=distribution, name="spec1")
        self.factory.makeSpecification(
            distribution=distribution, name="spec2",
            status=SpecificationDefinitionStatus.OBSOLETE)
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        self.assertNamesOfSpecificationsAre(
            ["spec1"], distro_on_webservice.valid_specifications)

    def test_distroseries_all_specifications(self):
        distribution = self.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            name='maudlin', distribution=distribution)
        self.factory.makeSpecification(
            distribution=distribution, name="spec1",
            goal=distroseries)
        self.factory.makeSpecification(
            distribution=distribution, name="spec2",
            goal=distroseries)
        self.factory.makeSpecification(
            distribution=distribution, name="spec3")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        distroseries_on_webservice = distro_on_webservice.getSeries(
            name_or_version="maudlin")
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"],
            distroseries_on_webservice.all_specifications)

    # XXX: salgado, 2010-11-25, bug=681432: Test disabled because
    # DistroSeries.valid_specifications is broken.
    def disabled_test_distroseries_valid_specifications(self):
        distribution = self.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            name='maudlin', distribution=distribution)
        self.factory.makeSpecification(
            distribution=distribution, name="spec1",
            goal=distroseries)
        self.factory.makeSpecification(
            distribution=distribution, name="spec2",
            goal=distroseries)
        self.factory.makeSpecification(
            distribution=distribution, name="spec3",
            goal=distroseries,
            status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            distribution=distribution, name="spec4")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        distroseries_on_webservice = distro_on_webservice.getSeries(
            name_or_version="maudlin")
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"],
            distroseries_on_webservice.valid_specifications)

    def test_productseries_all_specifications(self):
        product = self.makeProduct()
        productseries = self.factory.makeProductSeries(
            product=product, name="fooix-dev")
        self.factory.makeSpecification(
            product=product, name="spec1", goal=productseries)
        self.factory.makeSpecification(
            product=product, name="spec2", goal=productseries)
        self.factory.makeSpecification(product=product, name="spec3")
        product_on_webservice = self.getPillarOnWebservice(product)
        series_on_webservice = product_on_webservice.getSeries(
            name="fooix-dev")
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], series_on_webservice.all_specifications)

    def test_productseries_valid_specifications(self):
        product = self.makeProduct()
        productseries = self.factory.makeProductSeries(
            product=product, name="fooix-dev")
        self.factory.makeSpecification(
            product=product, name="spec1", goal=productseries)
        self.factory.makeSpecification(
            product=product, name="spec2", goal=productseries)
        self.factory.makeSpecification(
            product=product, name="spec3", goal=productseries,
            status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(product=product, name="spec4")
        product_on_webservice = self.getPillarOnWebservice(product)
        series_on_webservice = product_on_webservice.getSeries(
            name="fooix-dev")
        # Should this be different to the results for distroseries?
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"],
            series_on_webservice.valid_specifications)

    def test_projectgroup_all_specifications(self):
        projectgroup = self.factory.makeProject()
        other_projectgroup = self.factory.makeProject()
        product1 = self.factory.makeProduct(project=projectgroup)
        product2 = self.factory.makeProduct(project=projectgroup)
        product3 = self.factory.makeProduct(project=other_projectgroup)
        self.factory.makeSpecification(
            product=product1, name="spec1")
        self.factory.makeSpecification(
            product=product2, name="spec2",
            status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            product=product3, name="spec3")
        projectgroup_on_webservice = self.getPillarOnWebservice(projectgroup)
        # Should this be different to the results for distroseries?
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"],
            projectgroup_on_webservice.all_specifications)

    def test_projectgroup_valid_specifications(self):
        projectgroup = self.factory.makeProject()
        other_projectgroup = self.factory.makeProject()
        product1 = self.factory.makeProduct(project=projectgroup)
        product2 = self.factory.makeProduct(project=projectgroup)
        product3 = self.factory.makeProduct(project=other_projectgroup)
        self.factory.makeSpecification(
            product=product1, name="spec1")
        self.factory.makeSpecification(
            product=product2, name="spec2",
            status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            product=product3, name="spec3")
        projectgroup_on_webservice = self.getPillarOnWebservice(projectgroup)
        # Should this be different to the results for distroseries?
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"],
            projectgroup_on_webservice.valid_specifications)

    def test_person_all_specifications(self):
        person = self.factory.makePerson(name="james-w")
        product = self.factory.makeProduct()
        self.factory.makeSpecification(
            product=product, name="spec1", drafter=person)
        self.factory.makeSpecification(
            product=product, name="spec2", approver=person,
            status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            product=product, name="spec3")
        launchpadlib = self.getLaunchpadlib()
        person_on_webservice = launchpadlib.load(
            str(launchpadlib._root_uri) + '/~james-w')
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], person_on_webservice.all_specifications)

    def test_person_valid_specifications(self):
        person = self.factory.makePerson(name="james-w")
        product = self.factory.makeProduct()
        self.factory.makeSpecification(
            product=product, name="spec1", drafter=person)
        self.factory.makeSpecification(
            product=product, name="spec2", approver=person,
            status=SpecificationDefinitionStatus.OBSOLETE)
        self.factory.makeSpecification(
            product=product, name="spec3")
        launchpadlib = self.getLaunchpadlib()
        person_on_webservice = launchpadlib.load(
            str(launchpadlib._root_uri) + '/~james-w')
        self.assertNamesOfSpecificationsAre(
            ["spec1"], person_on_webservice.valid_specifications)

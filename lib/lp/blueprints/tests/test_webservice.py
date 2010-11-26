# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad blueprints."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.testing.pages import webservice_for_person
from lp.blueprints.interfaces.specification import (
    SpecificationDefinitionStatus,
    )
from lp.testing import (
    launchpadlib_for, TestCaseWithFactory)


class SpecificationWebserviceTestCase(TestCaseWithFactory):

    def getLaunchpadlib(self):
        user = self.factory.makePerson()
        return launchpadlib_for("testing", user, version='devel')

    def getSpecOnWebservice(self, spec_object):
        launchpadlib = self.getLaunchpadlib()
        return launchpadlib.load(
            '/%s/+spec/%s' % (spec_object.target.name, spec_object.name))

    def getPillarOnWebservice(self, pillar_obj):
        # XXX: 2010-11-26, salgado, bug=681767: Can't use relative URLs here.
        launchpadlib = self.getLaunchpadlib()
        return launchpadlib.load(
            str(launchpadlib._root_uri) + '/' + pillar_obj.name)


class SpecificationAttributeWebserviceTests(SpecificationWebserviceTestCase):
    """Test accessing specification attributes over the webservice."""
    layer = DatabaseFunctionalLayer

    def test_representation_is_empty_on_1_dot_0(self):
        # ISpecification is exposed on the 1.0 version so that they can be
        # linked against branches, but none of its fields is exposed on that
        # version as we expect it to undergo significant refactorings before
        # it's ready for prime time.
        spec = self.factory.makeSpecification()
        user = self.factory.makePerson()
        webservice = webservice_for_person(user)
        response = webservice.get(
            '/%s/+spec/%s' % (spec.product.name, spec.name))
        expected_keys = sorted(
            [u'self_link', u'http_etag', u'resource_type_link'])
        self.assertEqual(response.status, 200)
        self.assertEqual(sorted(response.jsonBody().keys()), expected_keys)

    def test_representation_contains_name(self):
        spec = self.factory.makeSpecification()
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual(spec.name, spec_webservice.name)

    def test_representation_contains_target(self):
        spec = self.factory.makeSpecification(
            product=self.factory.makeProduct())
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual(spec.target.name, spec_webservice.target.name)

    def test_representation_contains_title(self):
        spec = self.factory.makeSpecification(title='Foo')
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual(spec.title, spec_webservice.title)

    def test_representation_contains_specification_url(self):
        spec = self.factory.makeSpecification(specurl='http://example.com')
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual(spec.specurl, spec_webservice.specification_url)

    def test_representation_contains_summary(self):
        spec = self.factory.makeSpecification(summary='Foo')
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual(spec.summary, spec_webservice.summary)

    def test_representation_contains_definition_status(self):
        spec = self.factory.makeSpecification()
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual(
            spec.definition_status.title, spec_webservice.definition_status)

    def test_representation_contains_assignee(self):
        # Hard-code the person's name or else we'd need to set up a zope
        # interaction as IPerson.name is protected.
        spec = self.factory.makeSpecification(
            assignee=self.factory.makePerson(name='test-person'))
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual('test-person', spec_webservice.assignee.name)

    def test_representation_contains_drafter(self):
        spec = self.factory.makeSpecification(
            drafter=self.factory.makePerson(name='test-person'))
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual('test-person', spec_webservice.drafter.name)

    def test_representation_contains_approver(self):
        spec = self.factory.makeSpecification(
            approver=self.factory.makePerson(name='test-person'))
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual('test-person', spec_webservice.approver.name)

    def test_representation_contains_owner(self):
        spec = self.factory.makeSpecification(
            owner=self.factory.makePerson(name='test-person'))
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual('test-person', spec_webservice.owner.name)

    def test_representation_contains_priority(self):
        spec = self.factory.makeSpecification()
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual(spec.priority.title, spec_webservice.priority)

    def test_representation_contains_date_created(self):
        spec = self.factory.makeSpecification()
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual(spec.datecreated, spec_webservice.date_created)

    def test_representation_contains_whiteboard(self):
        spec = self.factory.makeSpecification(whiteboard='Test')
        spec_webservice = self.getSpecOnWebservice(spec)
        self.assertEqual(spec.whiteboard, spec_webservice.whiteboard)

    def test_representation_contains_milestone(self):
        product = self.factory.makeProduct()
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
        product = self.factory.makeProduct(name="fooix")
        spec_object = self.factory.makeSpecification(
            product=product, name="some-spec")
        product_on_webservice = self.getPillarOnWebservice(product)
        spec = product_on_webservice.getSpecification(name="some-spec")
        self.assertEqual("some-spec", spec.name)
        self.assertEqual("fooix", spec.target.name)

    def test_get_specification_on_distribution(self):
        distribution = self.factory.makeDistribution(name="foobuntu")
        spec_object = self.factory.makeSpecification(
            distribution=distribution, name="some-spec")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        spec = distro_on_webservice.getSpecification(name="some-spec")
        self.assertEqual("some-spec", spec.name)
        self.assertEqual("foobuntu", spec.target.name)

    def test_get_specification_on_productseries(self):
        product = self.factory.makeProduct(name="fooix")
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
        distribution = self.factory.makeDistribution(name="foobuntu")
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
        product = self.factory.makeProduct()
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
        product = self.factory.makeProduct()
        self.factory.makeSpecification(product=product, name="spec1")
        self.factory.makeSpecification(product=product, name="spec2")
        product_on_webservice = self.getPillarOnWebservice(product)
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], product_on_webservice.all_specifications)

    def test_product_valid_specifications(self):
        product = self.factory.makeProduct()
        self.factory.makeSpecification(product=product, name="spec1")
        self.factory.makeSpecification(
            product=product, name="spec2",
            status=SpecificationDefinitionStatus.OBSOLETE)
        product_on_webservice = self.getPillarOnWebservice(product)
        self.assertNamesOfSpecificationsAre(
            ["spec1"], product_on_webservice.valid_specifications)

    def test_distribution_all_specifications(self):
        distribution = self.factory.makeDistribution()
        self.factory.makeSpecification(
            distribution=distribution, name="spec1")
        self.factory.makeSpecification(
            distribution=distribution, name="spec2")
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        self.assertNamesOfSpecificationsAre(
            ["spec1", "spec2"], distro_on_webservice.all_specifications)

    def test_distribution_valid_specifications(self):
        distribution = self.factory.makeDistribution()
        self.factory.makeSpecification(
            distribution=distribution, name="spec1")
        self.factory.makeSpecification(
            distribution=distribution, name="spec2",
            status=SpecificationDefinitionStatus.OBSOLETE)
        distro_on_webservice = self.getPillarOnWebservice(distribution)
        self.assertNamesOfSpecificationsAre(
            ["spec1"], distro_on_webservice.valid_specifications)

    def test_distroseries_all_specifications(self):
        distribution = self.factory.makeDistribution()
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
        distribution = self.factory.makeDistribution()
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
        product = self.factory.makeProduct()
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
        product = self.factory.makeProduct()
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

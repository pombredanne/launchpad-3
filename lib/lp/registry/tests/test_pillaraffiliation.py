# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for adapters."""

__metaclass__ = type

from storm.store import Store
from testtools.matchers import Equals
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.model.pillaraffiliation import IHasAffiliation
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount


class TestPillarAffiliation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def _check_affiliated_with_distro(self, person, distro, role):
        [badge] = IHasAffiliation(distro).getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/distribution-badge", "Pting %s" % role), badge)

    def test_distro_owner_affiliation(self):
        # A person who owns a distro is affiliated.
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=person, name='pting')
        self._check_affiliated_with_distro(person, distro, 'maintainer')

    def test_distro_driver_affiliation(self):
        # A person who is a distro driver is affiliated.
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(driver=person, name='pting')
        self._check_affiliated_with_distro(person, distro, 'driver')

    def test_distro_team_driver_affiliation(self):
        # A person who is a member of the distro driver team is affiliated.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(members=[person])
        distro = self.factory.makeDistribution(driver=team, name='pting')
        self._check_affiliated_with_distro(person, distro, 'driver')

    def test_no_distro_security_contact_affiliation(self):
        # A person who is the security contact for a distro is not affiliated
        # for simple distro affiliation checks.
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(security_contact=person)
        self.assertIs(
            None, IHasAffiliation(distro).getAffiliationBadges([person])[0])

    def test_no_distro_bug_supervisor_affiliation(self):
        # A person who is the bug supervisor for a distro is not affiliated
        # for simple distro affiliation checks.
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(bug_supervisor=person)
        self.assertIs(
            None, IHasAffiliation(distro).getAffiliationBadges([person])[0])

    def _check_affiliated_with_product(self, person, product, role):
        [badge] = IHasAffiliation(product).getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/product-badge", "Pting %s" % role), badge)

    def test_product_driver_affiliation(self):
        # A person who is the driver for a product is affiliated.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(driver=person, name='pting')
        self._check_affiliated_with_product(person, product, 'driver')

    def test_product_team_driver_affiliation(self):
        # A person who is a member of the product driver team is affiliated.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(members=[person])
        product = self.factory.makeProduct(driver=team, name='pting')
        self._check_affiliated_with_product(person, product, 'driver')

    def test_product_group_driver_affiliation(self):
        # A person who is the driver for a product's group is affiliated.
        person = self.factory.makePerson()
        project = self.factory.makeProject(driver=person)
        product = self.factory.makeProduct(project=project, name='pting')
        self._check_affiliated_with_product(person, product, 'driver')

    def test_no_product_security_contact_affiliation(self):
        # A person who is the security contact for a product is is not
        # affiliated for simple product affiliation checks.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(security_contact=person)
        self.assertIs(
            None, IHasAffiliation(product).getAffiliationBadges([person])[0])

    def test_no_product_bug_supervisor_affiliation(self):
        # A person who is the bug supervisor for a product is is not
        # affiliated for simple product affiliation checks.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(bug_supervisor=person)
        self.assertIs(
            None, IHasAffiliation(product).getAffiliationBadges([person])[0])

    def test_product_owner_affiliation(self):
        # A person who owns a product is affiliated.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(owner=person, name='pting')
        self._check_affiliated_with_product(person, product, 'maintainer')

    def test_distro_affiliation_multiple_people(self):
        # A collection of people associated with a distro are affiliated.
        people = [self.factory.makePerson() for x in range(3)]
        distro = self.factory.makeDistribution(owner=people[0],
                                               driver=people[1],
                                               name='pting')
        badges = IHasAffiliation(distro).getAffiliationBadges(people)
        self.assertEqual(
            ("/@@/distribution-badge", "Pting maintainer"), badges[0])
        self.assertEqual(
            ("/@@/distribution-badge", "Pting driver"), badges[1])
        self.assertIs(None, badges[2])


class _TestBugTaskorBranchMixin:

    def test_distro_security_contact_affiliation(self):
        # A person who is the security contact for a distro is affiliated.
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(
            security_contact=person, name='pting')
        self._check_affiliated_with_distro(person, distro, 'security contact')

    def test_distro_bug_supervisor_affiliation(self):
        # A person who is the bug supervisor for a distro is affiliated.
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(
            bug_supervisor=person, name='pting')
        self._check_affiliated_with_distro(person, distro, 'bug supervisor')

    def test_product_security_contact_affiliation(self):
        # A person who is the security contact for a distro is affiliated.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(
            security_contact=person, name='pting')
        self._check_affiliated_with_product(
            person, product, 'security contact')

    def test_product_bug_supervisor_affiliation(self):
        # A person who is the bug supervisor for a distro is affiliated.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(
            bug_supervisor=person, name='pting')
        self._check_affiliated_with_product(person, product, 'bug supervisor')


class TestBugTaskPillarAffiliation(_TestBugTaskorBranchMixin,
                                   TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_correct_pillar_is_used(self):
        bugtask = self.factory.makeBugTask()
        adapter = IHasAffiliation(bugtask)
        self.assertEqual(bugtask.pillar, adapter.getPillar())

    def _check_affiliated_with_distro(self, person, target, role):
        bugtask = self.factory.makeBugTask(target=target)
        [badge] = IHasAffiliation(bugtask).getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/distribution-badge", "Pting %s" % role), badge)

    def _check_affiliated_with_product(self, person, target, role):
        bugtask = self.factory.makeBugTask(target=target)
        [badge] = IHasAffiliation(bugtask).getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/product-badge", "Pting %s" % role), badge)

    def test_product_affiliation_query_count(self):
        # Only 4 queries are expected, selects from:
        # - Bug, BugTask, Product, Person
        person = self.factory.makePerson()
        product = self.factory.makeProduct(owner=person, name='pting')
        bugtask = self.factory.makeBugTask(target=product)
        Store.of(bugtask).invalidate()
        with StormStatementRecorder() as recorder:
            IHasAffiliation(bugtask).getAffiliationBadges([person])
        self.assertThat(recorder, HasQueryCount(Equals(4)))

    def test_distro_affiliation_query_count(self):
        # Only 4 queries are expected, selects from:
        # - Bug, BugTask, Distribution, Person
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=person, name='pting')
        bugtask = self.factory.makeBugTask(target=distro)
        Store.of(bugtask).invalidate()
        with StormStatementRecorder() as recorder:
            IHasAffiliation(bugtask).getAffiliationBadges([person])
        self.assertThat(recorder, HasQueryCount(Equals(4)))


class TestBranchPillarAffiliation(_TestBugTaskorBranchMixin,
                                  TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_correct_pillar_is_used(self):
        branch = self.factory.makeBranch()
        adapter = IHasAffiliation(branch)
        self.assertEqual(branch.product, adapter.getPillar())

    def _check_affiliated_with_distro(self, person, target, role):
        distroseries = self.factory.makeDistroSeries(distribution=target)
        sp = self.factory.makeSourcePackage(distroseries=distroseries)
        branch = self.factory.makeBranch(sourcepackage=sp)
        [badge] = IHasAffiliation(branch).getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/distribution-badge", "Pting %s" % role), badge)

    def _check_affiliated_with_product(self, person, target, role):
        branch = self.factory.makeBranch(product=target)
        [badge] = IHasAffiliation(branch).getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/product-badge", "Pting %s" % role), badge)


class TestDistroSeriesPillarAffiliation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_correct_pillar_is_used(self):
        series = self.factory.makeDistroSeries()
        adapter = IHasAffiliation(series)
        self.assertEqual(series.distribution, adapter.getPillar())

    def test_driver_affiliation(self):
        # A person who is the driver for a distroseries is affiliated.
        # Here, the affiliation is with the distribution of the series.
        owner = self.factory.makePerson()
        driver = self.factory.makePerson()
        distribution = self.factory.makeDistribution(
            owner=owner, driver=driver, name='pting')
        distroseries = self.factory.makeDistroSeries(
            registrant=driver, distribution=distribution)
        [badge] = IHasAffiliation(distroseries).getAffiliationBadges([driver])
        self.assertEqual(
            ("/@@/distribution-badge", "Pting driver"), badge)

    def test_distro_driver_affiliation(self):
        # A person who is the driver for a distroseries' distro is affiliated.
        # Here, the affiliation is with the distribution of the series.
        owner = self.factory.makePerson()
        driver = self.factory.makePerson()
        distribution = self.factory.makeDistribution(
            owner=owner, driver=driver, name='pting')
        distroseries = self.factory.makeDistroSeries(
            registrant=owner, distribution=distribution)
        [badge] = IHasAffiliation(distroseries).getAffiliationBadges([driver])
        self.assertEqual(
            ("/@@/distribution-badge", "Pting driver"), badge)


class TestProductSeriesPillarAffiliation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_correct_pillar_is_used(self):
        series = self.factory.makeProductSeries()
        adapter = IHasAffiliation(series)
        self.assertEqual(series.product, adapter.getPillar())

    def test_driver_affiliation(self):
        # A person who is the driver for a productseries is affiliated.
        # Here, the affiliation is with the product.
        owner = self.factory.makePerson()
        driver = self.factory.makePerson()
        product = self.factory.makeProduct(
            owner=owner, driver=driver, name='pting')
        productseries = self.factory.makeProductSeries(
            owner=driver, product=product)
        [badge] = IHasAffiliation(productseries)\
                                        .getAffiliationBadges([driver])
        self.assertEqual(
            ("/@@/product-badge", "Pting driver"), badge)

    def test_product_driver_affiliation(self):
        # A person who is the driver for a productseries' product is
        # affiliated. Here, the affiliation is with the product.
        owner = self.factory.makePerson()
        driver = self.factory.makePerson()
        product = self.factory.makeProduct(
            owner=owner, driver=driver, name='pting')
        productseries = self.factory.makeProductSeries(
            owner=owner, product=product)
        [badge] = IHasAffiliation(productseries)\
                                        .getAffiliationBadges([driver])
        self.assertEqual(
            ("/@@/product-badge", "Pting driver"), badge)

    def test_product_group_driver_affiliation(self):
        # A person who is the driver for a productseries' product's group is
        # affiliated. Here, the affiliation is with the product.
        owner = self.factory.makePerson()
        driver = self.factory.makePerson()
        project = self.factory.makeProject(driver=driver)
        product = self.factory.makeProduct(
            owner=owner, project=project, name='pting')
        productseries = self.factory.makeProductSeries(
            owner=owner, product=product)
        [badge] = IHasAffiliation(productseries)\
                                        .getAffiliationBadges([driver])
        self.assertEqual(
            ("/@@/product-badge", "Pting driver"), badge)


class TestQuestionPillarAffiliation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_correct_pillar_is_used_for_product(self):
        product = self.factory.makeProduct()
        question = self.factory.makeQuestion(target=product)
        adapter = IHasAffiliation(question)
        self.assertEqual(question.product, adapter.getPillar())

    def test_correct_pillar_is_used_for_distribution(self):
        distribution = self.factory.makeDistribution()
        question = self.factory.makeQuestion(target=distribution)
        adapter = IHasAffiliation(question)
        self.assertEqual(question.distribution, adapter.getPillar())

    def test_correct_pillar_is_used_for_distro_sourcepackage(self):
        distribution = self.factory.makeDistribution()
        distro_sourcepackage = self.factory.makeDistributionSourcePackage(
            distribution=distribution)
        owner = self.factory.makePerson()
        question = self.factory.makeQuestion(
            target=distro_sourcepackage, owner=owner)
        adapter = IHasAffiliation(question)
        self.assertEqual(distribution, adapter.getPillar())

    def test_answer_contact_affiliation_for_distro(self):
        # A person is affiliated if they are an answer contact for a distro
        # target. Even if they also own the distro, the answer contact
        # affiliation takes precedence.
        answer_contact = self.factory.makePerson()
        english = getUtility(ILanguageSet)['en']
        answer_contact.addLanguage(english)
        distro = self.factory.makeDistribution(owner=answer_contact)
        with person_logged_in(answer_contact):
            distro.addAnswerContact(answer_contact, answer_contact)
        question = self.factory.makeQuestion(target=distro)
        [badge] = IHasAffiliation(question)\
                                    .getAffiliationBadges([answer_contact])
        self.assertEqual(
            ("/@@/distribution-badge", "%s answer contact" %
                distro.displayname), badge)

    def test_answer_contact_affiliation_for_distro_sourcepackage(self):
        # A person is affiliated if they are an answer contact for a dsp
        # target. Even if they also own the distro, the answer contact
        # affiliation takes precedence.
        answer_contact = self.factory.makePerson()
        english = getUtility(ILanguageSet)['en']
        answer_contact.addLanguage(english)
        distribution = self.factory.makeDistribution(owner=answer_contact)
        distro_sourcepackage = self.factory.makeDistributionSourcePackage(
            distribution=distribution)
        with person_logged_in(answer_contact):
            distro_sourcepackage.addAnswerContact(
                answer_contact, answer_contact)
        question = self.factory.makeQuestion(
            target=distro_sourcepackage, owner=answer_contact)
        [badge] = IHasAffiliation(question)\
                                    .getAffiliationBadges([answer_contact])
        self.assertEqual(
            ("/@@/distribution-badge", "%s answer contact" %
                distro_sourcepackage.displayname), badge)

    def test_answer_contact_affiliation_for_distro_sourcepackage_distro(self):
        # A person is affiliated if they are an answer contact for a dsp
        # target's distro. Even if they also own the distro, the answer
        # contact affiliation takes precedence.
        answer_contact = self.factory.makePerson()
        english = getUtility(ILanguageSet)['en']
        answer_contact.addLanguage(english)
        distribution = self.factory.makeDistribution(owner=answer_contact)
        distro_sourcepackage = self.factory.makeDistributionSourcePackage(
            distribution=distribution)
        with person_logged_in(answer_contact):
            distribution.addAnswerContact(answer_contact, answer_contact)
        question = self.factory.makeQuestion(
            target=distro_sourcepackage, owner=answer_contact)
        [badge] = IHasAffiliation(question)\
                                    .getAffiliationBadges([answer_contact])
        self.assertEqual(
            ("/@@/distribution-badge", "%s answer contact" %
                distribution.displayname), badge)

    def test_answer_contact_affiliation_for_product(self):
        # A person is affiliated if they are an answer contact for a product
        # target. Even if they also own the product, the answer contact
        # affiliation takes precedence.
        answer_contact = self.factory.makePerson()
        english = getUtility(ILanguageSet)['en']
        answer_contact.addLanguage(english)
        product = self.factory.makeProduct(owner=answer_contact)
        with person_logged_in(answer_contact):
            product.addAnswerContact(answer_contact, answer_contact)
        question = self.factory.makeQuestion(target=product)
        [badge] = IHasAffiliation(question)\
                                    .getAffiliationBadges([answer_contact])
        self.assertEqual(
            ("/@@/product-badge", "%s answer contact" %
                product.displayname), badge)

    def test_product_affiliation(self):
        # A person is affiliated if they are affiliated with the product.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(owner=person)
        question = self.factory.makeQuestion(target=product)
        [badge] = IHasAffiliation(question).getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/product-badge", "%s maintainer" %
                product.displayname), badge)

    def test_distribution_affiliation(self):
        # A person is affiliated if they are affiliated with the distribution.
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=person)
        question = self.factory.makeQuestion(target=distro)
        [badge] = IHasAffiliation(question).getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/distribution-badge", "%s maintainer" %
                distro.displayname), badge)


class TestSpecificationPillarAffiliation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_correct_pillar_is_used_for_product(self):
        product = self.factory.makeProduct()
        specification = self.factory.makeSpecification(product=product)
        adapter = IHasAffiliation(specification)
        self.assertEqual(specification.product, adapter.getPillar())

    def test_correct_pillar_is_used_for_distribution(self):
        distro = self.factory.makeDistribution()
        specification = self.factory.makeSpecification(distribution=distro)
        adapter = IHasAffiliation(specification)
        self.assertEqual(specification.distribution, adapter.getPillar())

    def test_product_affiliation(self):
        # A person is affiliated if they are affiliated with the pillar.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(owner=person)
        specification = self.factory.makeSpecification(product=product)
        [badge] = IHasAffiliation(specification)\
                                        .getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/product-badge", "%s maintainer" %
                product.displayname), badge)

    def test_distribution_affiliation(self):
        # A person is affiliated if they are affiliated with the distribution.
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=person)
        specification = self.factory.makeSpecification(distribution=distro)
        [badge] = IHasAffiliation(specification)\
                                        .getAffiliationBadges([person])
        self.assertEqual(
            ("/@@/distribution-badge", "%s maintainer" %
                distro.displayname), badge)

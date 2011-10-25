# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lazr.restfulclient.errors import ClientError
from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.registry.interfaces.projectgroup import IProjectGroupSet
from lp.testing import (
    launchpadlib_for,
    login_celebrity,
    login_person,
    TestCaseWithFactory,
    )


class TestProjectGroup(TestCaseWithFactory):
    """Tests project group object."""

    layer = DatabaseFunctionalLayer

    def test_pillar_category(self):
        # The pillar category is correct.
        pg = self.factory.makeProject()
        self.assertEqual("Project Group", pg.pillar_category)


class ProjectGroupSearchTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(ProjectGroupSearchTestCase, self).setUp()
        self.person = self.factory.makePerson()
        self.project1 = self.factory.makeProject(
            name="zazzle", owner=self.person)
        self.project2 = self.factory.makeProject(
            name="zazzle-dazzle", owner=self.person)
        self.project3 = self.factory.makeProject(
            name="razzle-dazzle", owner=self.person,
            description="Giving 110% at all times.")
        self.projectset = getUtility(IProjectGroupSet)
        login_person(self.person)

    def testSearchNoMatch(self):
        # Search for a string that does not exist.
        results = self.projectset.search(
            text="Fuzzle", search_products=False)
        self.assertEqual(0, results.count())

    def testSearchMatch(self):
        # Search for a matching string.
        results = self.projectset.search(
            text="zazzle", search_products=False)
        self.assertEqual(2, results.count())
        expected = sorted([self.project1, self.project2])
        self.assertEqual(expected, sorted(results))

    def testSearchDifferingCaseMatch(self):
        # Search for a matching string with a different case.
        results = self.projectset.search(
            text="Zazzle", search_products=False)
        self.assertEqual(2, results.count())
        expected = sorted([self.project1, self.project2])
        self.assertEqual(expected, sorted(results))

    def testProductSearchNoMatch(self):
        # Search for only project even if a product matches.
        product = self.factory.makeProduct(
            name="zazzle-product",
            title="Hoozah",
            owner=self.person)
        product.project = self.project1
        results = self.projectset.search(
            text="Hoozah", search_products=False)
        self.assertEqual(0, results.count())

    def testProductSearchMatch(self):
        # Search for products belonging to a project.  Note the project is
        # returned.
        product = self.factory.makeProduct(
            name="zazzle-product",
            title="Hoozah",
            owner=self.person)
        product.project = self.project1
        results = self.projectset.search(
            text="Hoozah", search_products=True)
        self.assertEqual(1, results.count())
        self.assertEqual(self.project1, results[0])

    def testProductSearchMatchOnProject(self):
        # Use the 'search_products' option but only look for a matching
        # project group to demonstrate projects are NOT searched too.

        # XXX: BradCrittenden 2009-11-10 bug=479984:
        # The behavior is currently unintuitive when search_products is used.
        # An exact match on a project is not returned since only products are
        # searched and the corresponding project for those matched is
        # returned.  This test demonstrates the current wrong behavior and
        # needs to be fixed when the search is fixed.
        results = self.projectset.search(
            text="zazzle-dazzle", search_products=True)
        self.assertEqual(0, results.count())

    def testProductSearchPercentMatch(self):
        # Search including a percent sign.  The match succeeds and does not
        # raise an exception.
        results = self.projectset.search(
            text="110%", search_products=False)
        self.assertEqual(1, results.count())
        self.assertEqual(self.project3, results[0])


class TestProjectGroupPermissions(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProjectGroupPermissions, self).setUp()
        self.pg = self.factory.makeProject(name='my-project-group')

    def test_attribute_changes_by_admin(self):
        login_celebrity('admin')
        self.pg.name = 'new-name'
        self.pg.owner = self.factory.makePerson(name='project-group-owner')

    def test_attribute_changes_by_registry_admin(self):
        login_celebrity('registry_experts')
        new_owner = self.factory.makePerson(name='project-group-owner')
        self.pg.name = 'new-name'
        self.assertRaises(
            Unauthorized, setattr, self.pg, 'owner', new_owner)

    def test_attribute_changes_by_owner(self):
        login_person(self.pg.owner)
        self.assertRaises(
            Unauthorized, setattr, self.pg, 'name', 'new-name')
        self.pg.owner = self.factory.makePerson(name='project-group-owner')


class TestLaunchpadlibAPI(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_inappropriate_deactivation_does_not_cause_an_OOPS(self):
        # Make sure a 400 error and not an OOPS is returned when a ValueError
        # is raised when trying to deactivate a project that has source
        # releases.
        launchpad = launchpadlib_for("test", "salgado", "WRITE_PUBLIC")
        project = launchpad.projects['evolution']
        project.active = False
        e = self.assertRaises(ClientError, project.lp_save)

        # no OOPS was generated as a result of the exception
        self.assertEqual([], self.oopses)
        self.assertEqual(400, e.response.status)
        self.assertIn(
            'This project cannot be deactivated since it is linked to source '
            'packages.', e.content)

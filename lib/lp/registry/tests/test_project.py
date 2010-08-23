# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import login
from canonical.testing import LaunchpadFunctionalLayer
from lp.registry.interfaces.projectgroup import IProjectGroupSet
from lp.testing import TestCaseWithFactory


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
        login(self.person.preferredemail.email)

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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

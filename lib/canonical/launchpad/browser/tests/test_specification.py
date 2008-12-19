# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy
from zope.testing.doctest import DocTestSuite

from canonical.launchpad.browser import specification
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.lazr.testing.webservice import FakeRequest
from canonical.testing.layers import DatabaseFunctionalLayer


class TestBranchTraversal(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.specification = self.factory.makeSpecification()

    def assertRedirects(self, segments, url):
        redirection = self.traverse(segments)
        self.assertEqual(url, redirection.target)

    def linkBranch(self, branch):
        # XXX: JonathanLange 2008-12-19: Remove the security proxy since
        # linkBranch sets date_last_modified on branch directly. Is this a bug
        # in linkBranch?
        self.specification.linkBranch(
            removeSecurityProxy(branch), self.factory.makePerson())

    def traverse(self, segments):
        stack = list(reversed(['+branch'] + segments))
        name = stack.pop()
        request = FakeRequest([], stack)
        traverser = specification.SpecificationNavigation(
            self.specification, request)
        return traverser.publishTraverse(request, name)

    def test_junk_branch(self):
        branch = self.factory.makeBranch(product=None)
        self.linkBranch(branch)
        segments = [branch.owner.name, '+junk', branch.name]
        self.assertEqual(
            self.specification.getBranchLink(branch), self.traverse(segments))

    def test_junk_branch_no_such_person(self):
        person_name = self.factory.getUniqueString()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person_name, '+junk', branch_name])

    def test_junk_branch_no_such_branch(self):
        person = self.factory.makePerson()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person.name, '+junk', branch_name])

    def test_product_branch(self):
        branch = self.factory.makeBranch()
        self.linkBranch(branch)
        segments = [branch.owner.name, branch.product.name, branch.name]
        self.assertEqual(
            self.specification.getBranchLink(branch), self.traverse(segments))

    def test_product_branch_no_such_person(self):
        person_name = self.factory.getUniqueString()
        product_name = self.factory.getUniqueString()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person_name, product_name, branch_name])

    def test_product_branch_no_such_product(self):
        person = self.factory.makePerson()
        product_name = self.factory.getUniqueString()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person.name, product_name, branch_name])

    def test_product_branch_no_such_branch(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person.name, product.name, branch_name])

    def test_package_branch(self):
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        branch = self.factory.makeBranch(
            distroseries=distroseries, sourcepackagename=sourcepackagename)
        self.linkBranch(branch)
        segments = [
            branch.owner.name,
            branch.distroseries.distribution.name,
            branch.distroseries.name,
            branch.sourcepackagename.name,
            branch.name]
        # XXX: JonathanLange 2008-12-19: What we want...
        #self.assertEqual(self.specification.getBranchLink(branch),
        #self.traverse(segments))
        self.assertRaises(NotFound, self.traverse, segments)



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(DocTestSuite(specification))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())


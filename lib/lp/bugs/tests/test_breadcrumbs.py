# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getMultiAdapter

from canonical.lazr.testing.menus import make_fake_request
from canonical.launchpad.webapp.publisher import RootObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import (
    ANONYMOUS, TestCaseWithFactory, login)


class TestBugTaskBreadcrumbBuilder(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTaskBreadcrumbBuilder, self).setUp()
        self.product = self.factory.makeProduct(
            name='crumb-tester', displayname="Crumb Tester")
        self.bug = self.factory.makeBug(product=self.product)
        self.root = RootObject()

    def test_bugtask_on_mainsite(self):
        request = make_fake_request(
            'http://launchpad.dev/%s/+bug/%d' % (
                self.product.name, self.bug.id),
            [self.root, self.product, self.bug.default_bugtask])
        hierarchy = getMultiAdapter((self.root, request), name='+hierarchy')
        self.assertEquals(
            ['http://launchpad.dev/crumb-tester',
             'http://launchpad.dev/crumb-tester/+bug/%d' % self.bug.id],
            [crumb.url for crumb in hierarchy.items()])
        self.assertEquals(
            ["Crumb Tester", "Bug #%d" % self.bug.id],
            [crumb.text for crumb in hierarchy.items()])

    def test_bugtask_on_vhost(self):
        request = make_fake_request(
            'http://bugs.launchpad.dev/%s/+bug/%d' % (
                self.product.name, self.bug.id),
            [self.root, self.product, self.bug.default_bugtask])
        hierarchy = getMultiAdapter((self.root, request), name='+hierarchy')
        self.assertEquals(
            ['http://bugs.launchpad.dev/crumb-tester',
             'http://bugs.launchpad.dev/crumb-tester/+bug/%d' % self.bug.id],
            [crumb.url for crumb in hierarchy.items()])
        self.assertEquals(
            ["Crumb Tester", "Bug #%d" % self.bug.id],
            [crumb.text for crumb in hierarchy.items()])

    def test_bugtask_child_on_vhost(self):
        request = make_fake_request(
            'http://bugs.launchpad.dev/%s/+bug/%d/+activity' % (
                self.product.name, self.bug.id),
            [self.root, self.product, self.bug.default_bugtask])
        hierarchy = getMultiAdapter((self.root, request), name='+hierarchy')
        self.assertEquals(
            ['http://bugs.launchpad.dev/crumb-tester',
             'http://bugs.launchpad.dev/crumb-tester/+bug/%d' % self.bug.id],
            [crumb.url for crumb in hierarchy.items()])
        self.assertEquals(
            ["Crumb Tester", "Bug #%d" % self.bug.id],
            [crumb.text for crumb in hierarchy.items()])

    def test_bugtask_private_bug(self):
        # A breadcrumb is not generated for a bug that the user does
        # not have permission to view.
        login('foo.bar@canonical.com')
        self.bug.setPrivate(True, self.bug.owner)
        login(ANONYMOUS)
        request = make_fake_request(
            'http://bugs.launchpad.dev/%s/+bug/%d/+activity' % (
                self.product.name, self.bug.id),
            [self.root, self.product, self.bug.default_bugtask])
        hierarchy = getMultiAdapter((self.root, request), name='+hierarchy')
        self.assertEquals(
            ['http://bugs.launchpad.dev/crumb-tester'],
            [crumb.url for crumb in hierarchy.items()])
        self.assertEquals(
            ["Crumb Tester"], [crumb.text for crumb in hierarchy.items()])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

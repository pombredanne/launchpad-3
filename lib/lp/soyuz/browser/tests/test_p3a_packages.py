# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401

"""Unit tests for TestP3APackages."""

__metaclass__ = type
__all__ = [
    'TestP3APackages',
    'test_suite',
    ]

import unittest

from zope.security.interfaces import Unauthorized

from canonical.testing import LaunchpadFunctionalLayer
from lp.testing import login, login_person, TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestP3APackages(TestCaseWithFactory):
    """P3A archive pages are rendered correctly."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestP3APackages, self).setUp()
        self.private_ppa = self.factory.makeArchive(description='Foo')
        login('admin@canonical.com')
        self.private_ppa.buildd_secret = 'blah'
        self.private_ppa.private = True
        self.joe = self.factory.makePerson(name='joe')
        self.fred = self.factory.makePerson(name='fred')
        login_person(self.private_ppa.owner)
        self.private_ppa.newSubscription(self.joe, self.private_ppa.owner)

    def test_packages_unauthorized(self):
        login_person(self.fred)
        self.assertRaises(
            Unauthorized, create_initialized_view, self.private_ppa,
            "+packages")

    def test_packages_authorized(self):
        login_person(self.joe)
        view = create_initialized_view(self.private_ppa, "+packages")
        html = view.__call__()
        self.failUnless('Packages in "Foo"' in html)

    def test_packages_link_unauthorized(self):
        login_person(self.fred)
        view = create_initialized_view(self.private_ppa, "+index")
        html = view.__call__()
        self.failUnless('View package details' not in html)

    def test_packages_link_authorized(self):
        login_person(self.joe)
        view = create_initialized_view(self.private_ppa, "+index")
        html = view.__call__()
        self.failUnless('View package details' in html)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

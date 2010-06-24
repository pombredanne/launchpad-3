# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401

"""Unit tests for TestP3APackages."""

__metaclass__ = type
__all__ = [
    'TestP3APackages',
    'TestPPAPackages',
    'test_suite',
    ]

import unittest

from zope.security.interfaces import Unauthorized

from canonical.testing import LaunchpadFunctionalLayer
from lp.soyuz.browser.archive import ArchiveNavigationMenu
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
        self.mary = self.factory.makePerson(name='mary')
        login_person(self.private_ppa.owner)
        self.private_ppa.newSubscription(self.joe, self.private_ppa.owner)
        self.private_ppa.newComponentUploader(self.mary, 'main')

    def test_packages_unauthorized(self):
        """A person with no subscription will not be able to view +packages
        """
        login_person(self.fred)
        self.assertRaises(
            Unauthorized, create_initialized_view, self.private_ppa,
            "+packages")

    def test_packages_unauthorized_subscriber(self):
        """A person with a subscription will not be able to view +packages
        """
        login_person(self.joe)
        self.assertRaises(
            Unauthorized, create_initialized_view, self.private_ppa,
            "+packages")

    def test_packages_authorized(self):
        """A person with launchpad.{Append,Edit} will be able to do so"""
        login_person(self.private_ppa.owner)
        view = create_initialized_view(self.private_ppa, "+packages")
        menu = ArchiveNavigationMenu(view)
        self.assertTrue(menu.packages().enabled)

    def test_packages_uploader(self):
        """A person with launchpad.Append will also be able to do so"""
        login_person(self.mary)
        view = create_initialized_view(self.private_ppa, "+packages")
        menu = ArchiveNavigationMenu(view)
        self.assertTrue(menu.packages().enabled)

    def test_packages_link_unauthorized(self):
        login_person(self.fred)
        view = create_initialized_view(self.private_ppa, "+index")
        menu = ArchiveNavigationMenu(view)
        self.assertFalse(menu.packages().enabled)

    def test_packages_link_subscriber(self):
        login_person(self.joe)
        view = create_initialized_view(self.private_ppa, "+index")
        menu = ArchiveNavigationMenu(view)
        self.assertFalse(menu.packages().enabled)


class TestPPAPackages(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestPPAPackages, self).setUp()
        self.joe = self.factory.makePerson(name='joe')
        self.ppa = self.factory.makeArchive()

    def test_ppa_packages(self):
        login_person(self.joe)
        view = create_initialized_view(self.ppa, "+index")
        menu = ArchiveNavigationMenu(view)
        self.assertTrue(menu.packages().enabled)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

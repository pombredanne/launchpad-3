#! /usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Tests for BranchPullListing and related."""

__metaclass__ = type

import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite

from canonical.database.constants import UTC_NOW
from canonical.launchpad import browser as browser
from canonical.launchpad.database import Branch
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase


class MockRequest:
    """A mock request.
    
    We are not using the standard zope one because SteveA said it was
    'crackful'.
    """


class MockResponse:
    """A mock response.
    
    We are not using the standard zope one because SteveA said it was
    'crackful'.
    """

    def __init__(self):
        self._calls = []

    def setHeader(self, header, value):
        self._calls.append(('setHeader', header, value))


class MockBranch:
    """A fake branch with a few interesting fields."""

    def __init__(self, id_, url):
        self.id = id_
        self.url = self.pull_url = url


class TestBranchPullWithBranches(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.view = browser.BranchPullListing(None, None)
        self.branch_with_product = MockBranch(3, u"http://foo/bar")
        self.branch_with_another_product = MockBranch(7, u"http://foo/gam")
        self.branch_with_no_product = MockBranch(19, u"sftp://example.com")


    def test_get_line_for_branch(self):
        self.assertEqual(
            self.view.get_line_for_branch(self.branch_with_product),
            "3 http://foo/bar")

    def test_branches_page(self):
        branches = [self.branch_with_product,
                    self.branch_with_another_product,
                    self.branch_with_no_product]
        expected = ("3 http://foo/bar\n"
                    "7 http://foo/gam\n"
                    "19 sftp://example.com\n")
        self.assertEqual(self.view.branches_page(branches), expected)


class TestBranchesToPullSample(LaunchpadFunctionalTestCase):

    def test_get_branches_to_pull(self):
        self.login()
        mock_request = MockRequest()
        mock_request.response = MockResponse()
        view = browser.BranchPullListing(None, mock_request)
        expected_ids = sorted([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
                               15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
        got_ids = sorted([branch.id for branch in view.get_branches_to_pull()])
        self.assertEqual(got_ids, expected_ids)
        # now check refresh logic: list any branch with either no last mirrored
        # time, or now - lastmirrored < 24 hours and not a supermirror branch.
        branch = Branch.get(23)
        branch.last_mirror_attempt = UTC_NOW
        branch.sync()
        expected_ids.remove(23)
        got_ids = sorted([branch.id for branch in view.get_branches_to_pull()])
        self.assertEqual(got_ids, expected_ids)
        # As we've finished this test we dont care about what we have created
        # in the database, if we could rollback that might be nice for clarity.

    def test_branch_pull_render(self):
        self.login()
        mock_request = MockRequest()
        mock_request.response = MockResponse()
        view = browser.BranchPullListing(None, mock_request)
        listing = view.render()
        self.assertEqual(listing[-1], '\n')
        expected = sorted([
            u'1 http://bazaar.ubuntu.com/mozilla@arch.ubuntu.com/mozilla--MAIN--0',
            u'2 http://bazaar.ubuntu.com/thunderbird@arch.ubuntu.com/thunderbird--MAIN--0',
            u'3 http://bazaar.ubuntu.com/twisted@arch.ubuntu.com/twisted--trunk--0',
            u'4 http://bazaar.ubuntu.com/bugzilla@arch.ubuntu.com/bugzila--MAIN--0',
            u'5 http://bazaar.ubuntu.com/arch@arch.ubuntu.com/arch--devel--1.0',
            u'6 http://bazaar.ubuntu.com/kiwi2@arch.ubuntu.com/kiwi2--MAIN--0',
            u'7 http://bazaar.ubuntu.com/plone@arch.ubuntu.com/plone--trunk--0',
            u'8 http://bazaar.ubuntu.com/gnome@arch.ubuntu.com/gnome--evolution--2.0',
            u'9 http://bazaar.ubuntu.com/iso-codes@arch.ubuntu.com/iso-codes--iso-codes--0.35',
            u'10 http://bazaar.ubuntu.com/mozilla@arch.ubuntu.com/mozilla--release--0.9.2',
            u'11 http://bazaar.ubuntu.com/mozilla@arch.ubuntu.com/mozilla--release--0.9.1',
            u'12 http://bazaar.ubuntu.com/mozilla@arch.ubuntu.com/mozilla--release--0.9',
            u'13 http://bazaar.ubuntu.com/mozilla@arch.ubuntu.com/mozilla--release--0.8',
            u'14 http://bazaar.ubuntu.com/gnome@arch.ubuntu.com/evolution--MAIN--0',
            u'15 http://example.com/gnome-terminal/main',
            u'16 http://example.com/gnome-terminal/2.6',
            u'17 http://example.com/gnome-terminal/2.4',
            u'18 http://trekkies.example.com/gnome-terminal/klingon',
            u'19 http://users.example.com/gnome-terminal/slowness',
            u'20 http://localhost:8000/a',
            u'21 http://localhost:8000/b',
            u'22 http://not.launchpad.server.com/',
            u'23 http://whynot.launchpad.server.com/',
            u'24 http://users.example.com/gnome-terminal/launchpad',
            u'25 /srv/sm-ng/pushsftp-hosted/00/00/00/19'])
            
        self.assertEqual(sorted(listing.splitlines()), expected)
        
    def test_branch_pull_mime_type(self):
        self.login()
        mock_request = MockRequest()
        mock_request.response = MockResponse()
        view = browser.BranchPullListing(None, mock_request)
        view.render()
        expected = [('setHeader', 'Content-type', 'text/plain')]
        self.assertEqual(mock_request.response._calls, expected)


def test_suite():
    loader = unittest.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

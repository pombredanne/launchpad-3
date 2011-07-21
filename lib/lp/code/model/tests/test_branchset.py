# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BranchSet."""

__metaclass__ = type

from testtools.matchers import LessThan

from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.branch import IBranchSet
from lp.code.model.branch import BranchSet
from lp.testing import (
    logout,
    TestCaseWithFactory,
    )
from lp.testing._webservice import QueryCollector
from lp.testing.matchers import HasQueryCount


class TestBranchSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_provides_IBranchSet(self):
        # BranchSet instances provide IBranchSet.
        self.assertProvides(BranchSet(), IBranchSet)

    def test_getByUrls(self):
        # getByUrls returns a list of branches matching the list of URLs that
        # it's given.
        a = self.factory.makeAnyBranch()
        b = self.factory.makeAnyBranch()
        branches = BranchSet().getByUrls(
            [a.bzr_identity, b.bzr_identity])
        self.assertEqual({a.bzr_identity: a, b.bzr_identity: b}, branches)

    def test_getByUrls_cant_find_url(self):
        # If a branch cannot be found for a URL, then None appears in the list
        # in place of the branch.
        url = 'http://example.com/doesntexist'
        branches = BranchSet().getByUrls([url])
        self.assertEqual({url: None}, branches)

    def test_api_branches_query_count(self):
        webservice = LaunchpadWebServiceCaller()
        collector = QueryCollector()
        collector.register()
        self.addCleanup(collector.unregister)
        # Get 'all' of the 50 branches this collection is limited to - rather
        # than the default in-test-suite pagination size of 5.
        url = "/branches?ws.size=50"
        logout()
        response = webservice.get(url,
            headers={'User-Agent': 'AnonNeedsThis'})
        self.assertEqual(response.status, 200,
            "Got %d for url %r with response %r" % (
            response.status, url, response.body))
        self.assertThat(collector, HasQueryCount(LessThan(17)))

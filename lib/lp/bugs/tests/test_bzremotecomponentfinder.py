# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests cronscript for retriving components from remote Bugzillas"""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.ftests import login_person
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad.scripts importFakeLogger

def read_test_file(name):
    """Return the contents of the test file named :name:

    Test files are located in lib/canonical/launchpad/ftests/testfiles
    """
    file_path = os.path.join(os.path.dirname(__file__), 'testfiles', name)
    test_file = open(file_path, 'r')
    return test_file.read()

class TestBugzillaRemoteComponentScraper(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugzillaRemoteComponentScraper, self).setUp()

    def test_url_correction(self):
        scraper = BugzillaRemoteComponentScraper(
            base_url="http://bugzilla.sample.com/")

        # Trailing slashes are stripped from the URL
        self.assertEqual(
            scraper.base_url,
            "http://bugzilla.sample.com")

        # Query cgi string is generated from the base_url
        self.assertEqual(
            scraper.url,
            "http://bugzilla.sample.com/query.cgi?format=advanced")

    def test_dict_from_csv(self):
        """Test conversion of various comma separated value strings parse correctly"""
        data = [
            {"'foo'":        {'foo':     {'name': 'foo'}}},
            {"'B_A_R'":      {'B_A_R':   {'name': 'B_A_R'}}},
            {"'b@z'":        {'b@z':     {'name': 'b@z'}}},
            {"'b\\!ah'":     {'b!ah':    {'name': 'b!ah'}}},
            {"42":           {42:        {'name': 42}}},
            {"''":           {'':        {'name': ''}}},
            {u"uni":         {'uni':     {'name': 'uni'}}},
            {u"fooŭbar":     {'fooŭbar': {'name': 'fooŭbar'}}},
            {"'a', 'b','c'": {'a':       {'name': 'a'},
                              'b':       {'name': 'a'},
                              'c':       {'name': 'a'},
                              }},
            }
        for key, true_dict in dict.items():
            test_dict = self.dictFromCSV(key)
            self.assertEqual(test_dict, true_dict)

    def test_parse_page(self):
        self.scraper = BugzillaRemoteComponentScraper(
            base_url="http://bugzilla.sample.com")

        page_text = read_test_file("bugzilla-fdo-advanced-query.html")

        self.scraper.parsePage(page_text)

        # TODO: Compare self.products with expected listing of products
        true_products = self.scraper.products
        self.assertEqual(self.scraper.products, true_products)

class TestBugzillaRemoteComponentFinder(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTrackerComponent, self).setUp()

        # TODO: Log in as whatever user runs the cronscript
        #regular_user = self.factory.makePerson()
        #login_person(regular_user)

    def test_get_remote_products_and_components(self):

        # TODO: Ensure data we're adding is not already there

        page_text = read_test_file("bugzilla-fdo-advanced-query.html")
        finder = BugzillaRemoteComponentFinder(
            txn=LaunchpadZopelessLayer.txn,
            logger=FakeLogger(),
            page_text=page_text)
        self.assertEqual(len(finder.products), 0)

        finder.getRemoteProductsAndComponents()

        # TODO: Validate that database now contains data we expect
        self.assertEqual(len(finder.products), 42)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))

    return suite

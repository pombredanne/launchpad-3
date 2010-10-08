# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests cronscript for retriving components from remote Bugzillas"""

__metaclass__ = type

__all__ = []

import os
import unittest

from canonical.testing import DatabaseFunctionalLayer
from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad.ftests import (
    login_person,
    login,
    logout,
    )
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.bzremotecomponentfinder import (
    BugzillaRemoteComponentFinder,
    BugzillaRemoteComponentScraper,
    dictFromCSV,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.sampledata import (
    ADMIN_EMAIL,
    )

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
            ("'foo'",        {'foo':     {'name': 'foo'}}),
            ("'B_A_R'",      {'B_A_R':   {'name': 'B_A_R'}}),
            ("'b@z'",        {'b@z':     {'name': 'b@z'}}),
            ("'b\\!ah'",     {'b!ah':    {'name': 'b!ah'}}),
            ("42",           {'42':      {'name': '42'}}),
            ("''",           {'':        {'name': ''}}),
            (u"uni",         {'uni':     {'name': 'uni'}}),
            ("'a', 'b','c'", {'a':       {'name': 'a'},
                              'b':       {'name': 'b'},
                              'c':       {'name': 'c'},
                              }),
            ]
        for test_case in data:
            (key, truth_dict) = test_case
            test_dict = dictFromCSV(key)
            self.assertEqual(test_dict, truth_dict)

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
        super(TestBugzillaRemoteComponentFinder, self).setUp()

        # TODO: Log in as whatever user runs the cronscript
        login(ADMIN_EMAIL)

    def test_get_remote_products_and_components(self):

        # TODO: Ensure data we're adding is not already there

        page_text = read_test_file("bugzilla-fdo-advanced-query.html")
        finder = BugzillaRemoteComponentFinder(
            txn=LaunchpadZopelessLayer.txn,
            logger=FakeLogger(),
            static_bugzilla_text=page_text)

        finder.getRemoteProductsAndComponents()

        # TODO: Validate that database now contains data we expect

    def test_cronjob(self):
        """Runs the cron job to verify it executes without error"""

        import subprocess
        process = subprocess.Popen(
            ['cronscripts/update-sourceforge-remote-products.py', '-v'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        (out, err) = process.communicate()

        self.assertEqual(out, '')
        self.assertEqual(process.returncode, 0)
        self.assertTrue('Creating lockfile' in err)
        self.assertTrue('Removing lock file' in err)
        self.assertTrue('ERROR' not in err)
        self.assertTrue('CRITICAL' not in err)
        self.assertTrue('Exception raised' not in err)

        print err

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))

    return suite

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the code import browser code."""

__metaclass__ = type

import re
import unittest

from canonical.launchpad.testing.pages import extract_text, find_tag_by_id
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.code.enums import RevisionControlSystems
from lp.testing import TestCaseWithFactory


class TestImportDetails(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def assertSvnDetailsDisplayed(self, svn_details, rcs_type, url):
        """Assert the `svn_details` tag described a Subversion import."""
        self.assertEquals(rcs_type.title, svn_details.span['title'])
        text = re.sub('\s+', ' ', extract_text(svn_details))
        self.assertTrue(
            text.startswith(
                'This branch is an import of the Subversion branch'))
        self.assertEquals(url, svn_details.a['href'])

    def test_bzr_svn_import(self):
        # The branch page for a bzr-svn-imported branch contains a summary of
        # the import details.
        bzr_svn_import = self.factory.makeCodeImport(
            rcs_type=RevisionControlSystems.BZR_SVN)
        browser = self.getUserBrowser(canonical_url(bzr_svn_import.branch))
        svn_details = find_tag_by_id(browser.contents, 'svn-import-details')
        self.assertSvnDetailsDisplayed(
            svn_details, RevisionControlSystems.BZR_SVN,
            bzr_svn_import.svn_branch_url)

    def test_cscvs_svn_import(self):
        # The branch page for a cscvs-imported svn branch contains a summary
        # of the import details.
        bzr_svn_import = self.factory.makeCodeImport(
            rcs_type=RevisionControlSystems.SVN)
        browser = self.getUserBrowser(canonical_url(bzr_svn_import.branch))
        svn_details = find_tag_by_id(browser.contents, 'svn-import-details')
        self.assertSvnDetailsDisplayed(
            svn_details, RevisionControlSystems.SVN,
            bzr_svn_import.svn_branch_url)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


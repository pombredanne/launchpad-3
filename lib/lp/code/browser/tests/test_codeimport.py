# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the code import browser code."""

__metaclass__ = type

import unittest

#from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.code.enums import RevisionControlSystems
from lp.testing import TestCaseWithFactory


class TestImportDetails(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_bzr_svn_import(self):
        # XXX
        bzr_svn_import = self.factory.makeCodeImport(
            rcs_type=RevisionControlSystems.BZR_SVN)
        browser = self.getUserBrowser(canonical_url(bzr_svn_import.branch))
        browser.getLink(bzr_svn_import.svn_branch_url)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


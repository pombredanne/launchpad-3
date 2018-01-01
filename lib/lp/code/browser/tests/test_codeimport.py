# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the code import browser code."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import re

from testtools.matchers import StartsWith
from zope.security.interfaces import Unauthorized

from lp.code.enums import (
    RevisionControlSystems,
    TargetRevisionControlSystems,
    )
from lp.code.tests.helpers import GitHostingFixture
from lp.services.webapp import canonical_url
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from lp.testing.views import create_initialized_view


class TestImportDetails(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def assertImportDetailsDisplayed(self, code_import, details_id,
                                     prefix_text, span_title=None):
        """A code import has its details displayed properly.

        :param code_import: An `ICodeImport`.
        :param details_id: The HTML tag id to search for.
        :param prefix_text: An expected prefix of the details text.
        :param span_title: If present, the expected contents of a span title
            attribute.
        """
        browser = self.getUserBrowser(canonical_url(code_import.target))
        details = find_tag_by_id(browser.contents, details_id)
        if span_title is not None:
            self.assertEqual(span_title, details.span['title'])
        text = re.sub('\s+', ' ', extract_text(details))
        self.assertThat(text, StartsWith(prefix_text))

    def test_bzr_svn_import(self):
        # The branch page for a bzr-svn-imported branch contains a summary
        # of the import details.
        code_import = self.factory.makeCodeImport(
            rcs_type=RevisionControlSystems.BZR_SVN)
        self.assertImportDetailsDisplayed(
            code_import, 'svn-import-details',
            'This branch is an import of the Subversion branch',
            span_title=RevisionControlSystems.BZR_SVN.title)

    def test_git_to_git_import(self):
        # The repository page for a git-to-git-imported repository contains
        # a summary of the import details.
        self.useFixture(GitHostingFixture())
        code_import = self.factory.makeCodeImport(
            rcs_type=RevisionControlSystems.GIT,
            target_rcs_type=TargetRevisionControlSystems.GIT)
        self.assertImportDetailsDisplayed(
            code_import, 'git-import-details',
            'This repository is an import of the Git repository')

    def test_branch_owner_of_import_forbidden(self):
        # Unauthorized users are forbidden to edit an import.
        cimport = self.factory.makeCodeImport()
        with person_logged_in(cimport.branch.owner):
            self.assertRaises(
                Unauthorized, create_initialized_view, cimport.branch,
                '+edit-import')

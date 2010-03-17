# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the product view classes and templates."""

__metaclass__ = type


from textwrap import dedent
import re

from canonical.testing import DatabaseFunctionalLayer

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.testing.pages import extract_text, find_main_content
from lp.testing import (TestCaseWithFactory)

class TestSourcePackageRecipe(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_index(self):
        chef = self.factory.makePersonNoCommit(displayname='Master Chef',
                name='chef')
        chocolate = self.factory.makeProduct(name='chocolate')
        cake_branch = self.factory.makeProductBranch(owner=chef, name='cake',
            product=chocolate)
        distroseries = self.factory.makeDistroSeries(
            displayname='Secret Squirrel')
        recipe = self.factory.makeSourcePackageRecipe(
            None, chef, distroseries, None, u'Cake Recipe', cake_branch)
        browser = self.getUserBrowser(canonical_url(recipe))
        pattern = re.compile(dedent("""\
            Master Chef
            Branches
            Description
            This recipe.*
            changes.
            Recipe Information
            Owner:
            Master Chef
            Base branch:
            lp://dev/~chef/chocolate/cake
            Debian version:
            1.0
            Distros:
            Secret Squirrel
            Build records
            Recipe contents
            # bzr-builder format 0.2 deb-version 1.0
            lp://dev/~chef/chocolate/cake"""))
        main_text = extract_text(find_main_content(browser.contents))
        self.assertTrue(pattern.search(main_text), main_text)

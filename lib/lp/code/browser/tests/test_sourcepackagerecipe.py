# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the product view classes and templates."""

__metaclass__ = type


from canonical.testing import DatabaseFunctionalLayer

from canonical.launchpad.webapp import canonical_url
from lp.testing import (TestCaseWithFactory)

class TestSourcePackageRecipe(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_index(self):
        recipe = self.factory.makeSourcePackageRecipe()
        browser = self.getUserBrowser(canonical_url(recipe, rootsite='code'))
        self.assertEqual('foo', browser.contents)

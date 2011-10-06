# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the specification dependency views.

There are also tests in lp/blueprints/stories/blueprints/xx-dependencies.txt.
"""

__metaclass__ = type

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import BrowserTestCase


class TestAddDependency(BrowserTestCase):
    layer = DatabaseFunctionalLayer

    def test_add_dependency_by_url(self):
        # It is possible to use the URL of a specification in the "Depends On"
        # field of the form to add a dependency to a spec.
        spec = self.factory.makeSpecification(owner=self.user)
        dependency = self.factory.makeSpecification()
        browser = self.getViewBrowser(spec, '+linkdependency')
        browser.getControl('Depends On').value = canonical_url(dependency)
        browser.getControl('Continue').click()
        self.assertIn(dependency, spec.dependencies)

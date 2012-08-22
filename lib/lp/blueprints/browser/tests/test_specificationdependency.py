# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the specification dependency views.

There are also tests in lp/blueprints/stories/blueprints/xx-dependencies.txt.
"""

__metaclass__ = type

from lp.services.webapp import canonical_url
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestAddDependency(BrowserTestCase):
    layer = DatabaseFunctionalLayer

    def test_add_dependency_by_url(self):
        # It is possible to use the URL of a specification in the "Depends On"
        # field of the form to add a dependency to a spec.
        spec = self.factory.makeSpecification(owner=self.user)
        dependency = self.factory.makeSpecification()
        dependency_url = canonical_url(dependency)
        browser = self.getViewBrowser(spec, '+linkdependency')
        browser.getControl('Depends On').value = dependency_url
        browser.getControl('Continue').click()
        # click() above issues a request, and
        # ZopePublication.endRequest() calls
        # zope.security.management.endInteraction().
        # We need a new interaction for the permission checks
        # on ISpecification objects.
        with person_logged_in(None):
            self.assertIn(dependency, spec.dependencies)

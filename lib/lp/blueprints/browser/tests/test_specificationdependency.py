# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type

import unittest

from canonical.launchpad.webapp import canonical_url
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import BrowserTestCase


class TestAddDependency(BrowserTestCase):
    layer = DatabaseFunctionalLayer

    def test_add_dependency_by_url(self):
        spec = self.factory.makeSpecification(owner=self.user)
        dependency = self.factory.makeSpecification()
        browser = self.getViewBrowser(spec, '+linkdependency')
        browser.getControl('Depends On').value = canonical_url(dependency)
        browser.getControl('Continue').click()
        self.assertIn(dependency, spec.dependencies)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

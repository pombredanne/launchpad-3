# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from lp.testing.publication import test_traverse
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)


class TestCodeImportMachineBreadcrumb(BaseBreadcrumbTestCase):
    """Test breadcrumbs for an `ICodeImportMachine`."""

    def test_machine(self):
        machine = self.factory.makeCodeImportMachine(hostname='apollo')
        import pdb; pdb.set_trace()
        url = canonical_url(machine)
        obj, request = test_traverse(url)
        crumbs = self.getBreadcrumbsForObject(machine)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

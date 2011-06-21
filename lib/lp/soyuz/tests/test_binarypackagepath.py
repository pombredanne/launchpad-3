# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Binary Package Path model."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.soyuz.interfaces.binarypackagepath import IBinaryPackagePathSet
from lp.testing import TestCaseWithFactory


class TestBinaryPackagePath(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_getOrCreate(self):
        bpp = getUtility(IBinaryPackagePathSet).getOrCreate('bin/bash')
        self.assertEqual('bin/bash', bpp.path)

    def test_getOrCreate_existing(self):
        orig_bpp = getUtility(IBinaryPackagePathSet).getOrCreate('bin/bash')
        bpp = getUtility(IBinaryPackagePathSet).getOrCreate('bin/bash')
        self.assertEqual(orig_bpp.id, bpp.id)

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Binary Package Path model."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.soyuz.interfaces.binarypackagepath import IBinaryPackagePathSource
from lp.testing import TestCaseWithFactory


class TestBinaryPackagePath(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_get_or_create(self):
        bpp = getUtility(IBinaryPackagePathSource).getOrCreate(u'bin/bash')
        self.assertEqual(u'bin/bash', bpp.path)

    def test_get_or_create_existing(self):
        orig_bpp = getUtility(IBinaryPackagePathSource).getOrCreate(
            u'bin/bash')
        bpp = getUtility(IBinaryPackagePathSource).getOrCreate(u'bin/bash')
        self.assertEqual(orig_bpp.id, bpp.id)

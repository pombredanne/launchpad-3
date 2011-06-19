# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Binary Package Release Contents model."""

__metaclass__ = type

import transaction

from zope.component import getUtility

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.archiveuploader.tests import datadir
from lp.soyuz.interfaces.binarypackagereleasecontents import (
    IBinaryPackageReleaseContentsSet,
    )
from lp.soyuz.model.binarypackagereleasecontents import (
    BinaryPackageReleaseContents,
    )
from lp.testing import TestCaseWithFactory


class TestBinaryPackagePath(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def create_bpr(self):
        bpr = self.factory.makeBinaryPackageRelease()
        deb = open(datadir('pmount_0.9.7-2ubuntu2_amd64.deb'), 'r')
        lfa = self.factory.makeLibraryFileAlias(
            filename='pmount_0.9.7-2ubuntu2_amd64.deb', content=deb.read())
        deb.close()
        transaction.commit()
        bpr.addFile(lfa)
        return bpr

    def test_add(self):
        bpr = self.create_bpr()
        getUtility(IBinaryPackageReleaseContentsSet).add(bpr)
        store = IStore(BinaryPackageReleaseContents)
        results = store.find(
            BinaryPackageReleaseContents,
            BinaryPackageReleaseContents.binarypackagerelease == bpr.id)
        self.assertEqual(13, results.count())

    def test_remove(self):
        bpr = self.create_bpr()
        getUtility(IBinaryPackageReleaseContentsSet).add(bpr)
        getUtility(IBinaryPackageReleaseContentsSet).remove(bpr)
        store = IStore(BinaryPackageReleaseContents)
        results = store.find(
            BinaryPackageReleaseContents,
            BinaryPackageReleaseContents.binarypackagerelease == bpr.id)
        self.assertEqual(0, results.count())

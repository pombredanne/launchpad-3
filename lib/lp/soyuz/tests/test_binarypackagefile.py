# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for `IBinaryPackageFile` and `IBinaryPackageFileSet`."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.soyuz.interfaces.files import IBinaryPackageFileSet
from lp.testing import TestCaseWithFactory
from lp.testing.matchers import Provides


class TestBinaryPackageFileSet(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def test_implements_interface(self):
        file_set = getUtility(IBinaryPackageFileSet)
        self.assertThat(file_set, Provides(IBinaryPackageFileSet))

    def test_loadLibraryFiles_returns_associated_lfas(self):
        bpf = self.factory.makeBinaryPackageFile()
        lfas = getUtility(IBinaryPackageFileSet).loadLibraryFiles([bpf])
        self.assertContentEqual([bpf.libraryfile], lfas)

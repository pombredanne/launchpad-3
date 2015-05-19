# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ArchiveArch features."""

from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.soyuz.interfaces.archivearch import IArchiveArchSet
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer


class TestArchiveArch(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestArchiveArch, self).setUp()

        self.archive_arch_set = getUtility(IArchiveArchSet)
        self.ppa = getUtility(IPersonSet).getByName('cprov').archive
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        self.ubuntu_archive = ubuntu.main_archive
        self.cell_proc = self.factory.makeProcessor(
            'cell-proc', 'PS cell processor', 'Screamingly faaaaaaaaaaaast',
            restricted=True, build_by_default=False)
        self.omap = self.factory.makeProcessor(
            'omap', 'Multimedia applications processor',
            'Does all your sound & video', restricted=True,
            build_by_default=False)

    def test_getByArchive_no_other_archives(self):
        # Test ArchiveArchSet.getByArchive returns no other archives.
        self.archive_arch_set.new(self.ppa, self.cell_proc)
        self.archive_arch_set.new(self.ubuntu_archive, self.omap)
        result = self.archive_arch_set.getByArchive(self.ppa)
        self.assertContentEqual([self.ppa], set(aa.archive for aa in result))

    def test_getByArchive_specific_architecture(self):
        # ArchiveArchSet.getByArchive can query for a specific architecture
        # association.
        self.archive_arch_set.new(self.ppa, self.cell_proc)
        self.archive_arch_set.new(self.ppa, self.omap)
        result_set = list(
            self.archive_arch_set.getByArchive(self.ppa, self.cell_proc))
        self.assertEqual(1, len(result_set))
        self.assertEqual(self.ppa, result_set[0].archive)
        self.assertEqual(self.cell_proc, result_set[0].processor)

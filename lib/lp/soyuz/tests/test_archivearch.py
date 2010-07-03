# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ArchiveArch features."""

import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer

from lp.testing import TestCaseWithFactory

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.soyuz.interfaces.archivearch import IArchiveArchSet
from lp.soyuz.interfaces.processor import IProcessorFamilySet

class TestArchiveArch(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestArchiveArch, self).setUp()

        self.ppa = getUtility(IPersonSet).getByName('cprov').archive
        pss = getUtility(IProcessorFamilySet)
        self.cell_proc = pss.new(
            'cell-proc', 'PS cell processor', 'Screamingly faaaaaaaaaaaast',
            True)
        self.omap = pss.new(
            'omap', 'Multimedia applications processor',
            'Does all your sound & video', True)

    def test_no_associations(self):
        """Our archive is not associated with any restricted processor
        families yet."""
        result_set = list(
            getUtility(IArchiveArchSet).getRestrictedfamilies(self.ppa))
        archivearches = [row[1] for row in result_set]
        self.assertTrue(all(aa is None for aa in archivearches))

    def test_single_association(self):
        """Our archive is now associated with one of the restricted processor
        families."""
        getUtility(IArchiveArchSet).new(self.ppa, self.cell_proc)
        result_set = list(
            getUtility(IArchiveArchSet).getRestrictedfamilies(self.ppa))
        results = dict(
            (row[0].name, row[1] is not None) for row in result_set)
        self.assertEquals(
            { 'arm' : False, 'cell-proc' : True, 'omap' : False},
            results)

    def test_get_by_archive(self):
        """Test ArchiveArchSet.getByArchive."""
        other_archive = getUtility(IDistributionSet)['ubuntu'].main_archive
        getUtility(IArchiveArchSet).new(self.ppa, self.cell_proc)
        getUtility(IArchiveArchSet).new(other_archive, self.omap)
        result_set = list(
            getUtility(IArchiveArchSet).getByArchive(self.ppa))
        self.assertEquals(1, len(result_set))
        self.assertEquals(self.ppa, result_set[0].archive)
        self.assertEquals(self.cell_proc, result_set[0].processorfamily)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for methods of PillarName and PillarNameSet."""

from zope.component import getUtility

from canonical.launchpad.ftests import login
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.registry.interfaces.pillar import IPillarNameSet
from lp.testing import TestCaseWithFactory


class TestPillarNameSet(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def test_search_correctly_ranks_by_aliases(self):
        """When we use a pillar's alias to search, that pillar will be the
        first one on the list.
        """
        login('mark@example.com')
        lz_foo = self.factory.makeProduct(name='lz-foo')
        lz_bar = self.factory.makeProduct(name='lz-bar')
        launchzap = self.factory.makeProduct(name='launchzap')
        launchzap.setAliases(['lz'])
        pillar_set = getUtility(IPillarNameSet)
        result_names = [
            pillar.name for pillar in pillar_set.search('lz', limit=5)]
        self.assertEquals(result_names, [u'launchzap', u'lz-bar', u'lz-foo'])

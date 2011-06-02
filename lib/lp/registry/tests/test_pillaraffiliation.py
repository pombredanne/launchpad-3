# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for adapters."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.model.pillaraffiliation import IHasAffiliation
from lp.testing import TestCaseWithFactory


class TestPillarAffiliation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_bugtask_distro_affiliation(self):
        # A person who owns a bugtask distro is affiliated.
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=person)
        bugtask = self.factory.makeBugTask(target=distro)
        badge = IHasAffiliation(bugtask).getAffiliationBadge(person)
        self.assertEqual(
            badge, ("distribution-badge", "Distribution affiliation"))

    def test_bugtask_product_affiliation(self):
        # A person who owns a bugtask product is affiliated.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(owner=person)
        bugtask = self.factory.makeBugTask(target=product)
        badge = IHasAffiliation(bugtask).getAffiliationBadge(person)
        self.assertEqual(
            badge, ("product-badge", "Product affiliation"))

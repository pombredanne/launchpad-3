# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for classes that implement IHasMergeProposals."""

__metaclass__ = type

import unittest

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.hasbranches import IHasMergeProposals
from lp.testing import TestCaseWithFactory


class TestIHasMergeProposals(TestCaseWithFactory):
    """Test that the correct objects implement the interface."""

    layer = DatabaseFunctionalLayer

    def test_product_implements_hasmergeproposals(self):
        # Products should implement IHasMergeProposals.
        product = self.factory.makeProduct()
        self.assertProvides(product, IHasMergeProposals)

    def test_person_implements_hasmergeproposals(self):
        # People should implement IHasMergeProposals.
        person = self.factory.makePerson()
        self.assertProvides(person, IHasMergeProposals)

    def test_project_implements_hasmergeproposals(self):
        # ProjectGroups should implement IHasMergeProposals.
        project = self.factory.makeProject()
        self.assertProvides(project, IHasMergeProposals)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


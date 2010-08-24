# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model tests for the DistroSeriesDifference class."""

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    )


class DistroSeriesDifferenceTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_implements_interface(self):
        ds_diff = self.factory.makeDistroSeriesDifference()

        verifyObject(IDistroSeriesDifference, ds_diff)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

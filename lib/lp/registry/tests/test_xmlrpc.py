# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing registry-related xmlrpc calls."""

__metaclass__ = type

import unittest

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.registry.interfaces.person import IPersonSetAPIView
from lp.registry.xmlrpc.personset import PersonSetAPIView
from lp.testing import TestCaseWithFactory


class TestPersonAPIGetOrCreate(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestPersonAPIGetOrCreate, self).setUp()
        self.personset_api = PersonSetAPIView(context=None, request=None)

    def test_provides_interface(self):
        self.assertProvides(self.personset_api, IPersonSetAPIView)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

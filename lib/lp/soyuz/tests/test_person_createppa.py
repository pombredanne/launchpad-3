# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test IPerson.createNewPPA()"""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import (
    PPACreationError,
    TeamSubscriptionPolicy,
    )
from lp.testing import TestCaseWithFactory
from zope.security.proxy import removeSecurityProxy


class TestCreateNewPPA(TestCaseWithFactory):
    """Test that the IPerson.createNewPPA method behaves as expected."""

    layer = DatabaseFunctionalLayer

    def test_create_ppa(self):
        person = self.factory.makePerson()
        ppa = person.createPPA()
        self.assertEqual(ppa.name, 'ppa')

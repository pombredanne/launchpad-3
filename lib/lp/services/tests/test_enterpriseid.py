# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Enterprise ID utilities."""

__metaclass__ = type

from lp.services.enterpriseid import (
    enterpriseid_to_object,
    object_to_enterpriseid,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestEnterpriseId(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_object_to_enterpriseid(self):
        person = self.factory.makePerson()
        eid = object_to_enterpriseid(person)
        expected = 'lp-development:Person:%d' % person.id
        self.assertEqual(expected, eid)

    def test_enterpriseid_to_object(self):
        person = self.factory.makePerson()
        eid = 'lp-development:Person:%d' % person.id
        obj = enterpriseid_to_object(eid)
        self.assertEqual(person, obj)

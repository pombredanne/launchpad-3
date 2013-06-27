# Copyright 2012-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Enterprise ID utilities."""

__metaclass__ = type

from testtools.matchers import Equals

from lp.services.database.interfaces import IStore
from lp.services.enterpriseid import (
    enterpriseids_to_objects,
    object_to_enterpriseid,
    )
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount


class TestEnterpriseId(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_object_to_enterpriseid(self):
        person = self.factory.makePerson()
        eid = object_to_enterpriseid(person)
        expected = 'lp-development:Person:%d' % person.id
        self.assertEqual(expected, eid)

    def test_enterpriseids_to_objects(self):
        expected = {}
        for x in range(10):
            person = self.factory.makePerson()
            expected['lp-development:Person:%d' % person.id] = person
        IStore(expected.values()[0].__class__).invalidate()
        with StormStatementRecorder() as recorder:
            objects = enterpriseids_to_objects(expected.keys())
        self.assertThat(recorder, HasQueryCount(Equals(1)))
        self.assertContentEqual(expected.keys(), objects.keys())
        self.assertContentEqual(expected.values(), objects.values())

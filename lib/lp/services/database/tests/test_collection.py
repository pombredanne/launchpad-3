# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `Collection`."""

__metaclass__ = type

import unittest

from storm.locals import Int, Storm
from storm.expr import LeftJoin
from zope.component import getUtility

from lp.services.database.collection import Collection
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from canonical.testing import ZopelessDatabaseLayer
from canonical.launchpad.interfaces.lpstorm import ISlaveStore
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


def get_store():
    return getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)


def make_table(range_start, range_end, table_name=None):
    """Create a temporary table and a storm class for it."""
    assert range_start < range_end, "Invalid range."
    if table_name is None:
        table_name = "TestTable"
    get_store().execute("""
       CREATE TEMP TABLE %s AS
       SELECT generate_series AS id
       FROM generate_series(%d, %d)
       """ % (table_name, range_start, range_end - 1))

    class TestTable(Storm):
        __storm_table__ = table_name
        id = Int(primary=True)
        def __init__(self, id):
            self.id = id
        def __eq__(self, other):
            return self.id == other.id

    return TestTable


def get_ids(testtable_objects):
    """Helper to unpack ids from a sequence of TestTable objects."""
    return [obj.id for obj in testtable_objects]


class CollectionTest(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_make_table(self):
        TestTable = make_table(1, 5)
        result = get_store().find(TestTable).order_by(TestTable.id)
        self.assertEqual(range(1, 5), get_ids(result))

    def test_select_one(self):
        TestTable = make_table(1, 5)
        collection = Collection(None, TestTable.id == 1)
        result = collection.select(TestTable)
        self.assertEqual([1], get_ids(result))

    def test_select_all(self):
        TestTable = make_table(1, 3)
        collection = Collection(None)
        result = collection.select(TestTable)
        self.assertContentEqual([1, 2], get_ids(result))

    def test_select_condition(self):
        TestTable = make_table(1, 5)
        collection = Collection(None, TestTable.id > 2)
        result = collection.select(TestTable)
        self.assertContentEqual([3, 4], get_ids(result))

    def test_select_conditions(self):
        TestTable = make_table(1, 5)
        collection = Collection(None, TestTable.id > 2, TestTable.id < 4)
        result = collection.select(TestTable)
        self.assertContentEqual([3], get_ids(result))

    def test_select_column(self):
        TestTable = make_table(1, 3)
        collection = Collection(None)
        result = collection.select(TestTable.id)
        self.assertContentEqual([1, 2], list(result))

    def test_copy_collection(self):
        TestTable = make_table(1, 3)
        collection = Collection(None)
        copied_collection = Collection(collection)
        result = copied_collection.select(TestTable)
        self.assertContentEqual([1, 2], get_ids(result))

    def test_restrict_collection(self):
        TestTable = make_table(1, 3)
        collection = Collection(None)
        copied_collection = Collection(collection, TestTable.id < 2)
        result = copied_collection.select(TestTable)
        self.assertContentEqual([1], get_ids(result))

    def test_select_join(self):
        TestTable1 = make_table(1, 2, 'TestTable1')
        TestTable2 = make_table(2, 3, 'TestTable2')
        collection = Collection(None)
        result = collection.select(TestTable1, TestTable2)
        self.assertEqual(
            [(TestTable1(id=1), TestTable2(id=2))], list(result))

    def test_select_join_column(self):
        TestTable1 = make_table(1, 2, 'TestTable1')
        TestTable2 = make_table(2, 3, 'TestTable2')
        collection = Collection(None)
        result = collection.select(TestTable1.id, TestTable2.id)
        self.assertEqual([(1, 2)], list(result))

    def test_select_partial_join(self):
        TestTable1 = make_table(1, 2, 'TestTable1')
        TestTable2 = make_table(2, 3, 'TestTable2')
        collection = Collection(None, TestTable2.id == TestTable1.id + 1)
        result = collection.select(TestTable1.id)
        self.assertEqual([1], list(result))

    def test_select_outer_join(self):
        TestTable1 = make_table(1, 3, 'TestTable1')
        TestTable2 = make_table(2, 4, 'TestTable2')

        # Add an outer-join table to the collection.
        collection = Collection(None).outer_join(
            TestTable2, TestTable2.id == TestTable1.id)
        result = collection.select(TestTable1.id, TestTable2.id)
        self.assertContentEqual([(1, None), (2, 2)], list(result))

    def test_select_store(self):
        TestTable = make_table(1, 2)
        collection = Collection(None)
        store = ISlaveStore(TestTable)
        expected_obj = TestTable(1)
        store.find = FakeMethod(result=[expected_obj])
        result_obj = collection.use(store).select(TestTable)[0]
        self.assertEqual(expected_obj, result_obj)
        self.assertNotEqual(0, store.find.call_count)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

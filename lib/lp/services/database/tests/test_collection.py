# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `Collection`."""

__metaclass__ = type

import unittest

from storm.locals import Storm, Int
from zope.component import getUtility

from lp.services.database.collection import Collection
from lp.testing import TestCaseWithFactory
from canonical.testing import ZopelessDatabaseLayer
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


class TestTable(Storm):

    __storm_table__ = 'TestTable'

    id = Int(primary=True)


def get_store():
    return getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

def make_table(range_start, range_end):
    """Create a temporary table."""
    assert range_start < range_end, "Invalid range."
    get_store().execute("""
       CREATE TEMP TABLE TestTable AS
       SELECT generate_series AS id
       FROM generate_series(%d, %d)
       """ % (range_start, range_end - 1))


def get_ids(testtable_rows):
    """Helper to unpack ids from a sequence of TestTable objects."""
    return [row.id for row in testtable_rows] 

class CollectionTest(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_make_table(self):
        make_table(1, 5)
        result = get_store().find(TestTable).order_by(TestTable.id)
        self.assertEqual(range(1, 5), get_ids(result))

    def test_select_one(self):
        make_table(1, 5)
        collection = Collection(None, TestTable.id == 1)
        result = collection.select(TestTable)
        self.assertEqual([1], get_ids(result))

    def test_select_all(self):
        make_table(1, 3)
        collection = Collection(None)
        result = collection.select(TestTable)
        self.assertContentEqual([1, 2], get_ids(result))

    def test_select_condition(self):
        make_table(1, 5)
        collection = Collection(None, TestTable.id > 2)
        result = collection.select(TestTable)
        self.assertContentEqual([3, 4], get_ids(result))

    def test_select_column(self):
        pass

    def test_copy_collection(self):
        pass

    def test_restrict_collection(self):
        pass

    def test_select_join(self):
        pass

    def test_select_join_column(self):
        pass

    def test_select_join_class_and_column(self):
        pass

    def test_select_partial_join(self):
        pass

    def test_select_outer_join(self):
        pass

    def test_select_store(self):
        pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

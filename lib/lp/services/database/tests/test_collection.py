# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `Collection`."""

__metaclass__ = type

import unittest

from storm.locals import Storm, Int
from zope.component import getUtility

from lp.testing import TestCaseWithFactory
from canonical.testing import ZopelessDatabaseLayer
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


class TestTable(Storm):

    __storm_table__ = 'TestTable'

    id = Int(primary=True)


def get_store():
    return getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

def make_table(store, first_id, last_id):
    """Create a temporary table."""
    store.execute("""
       CREATE TEMP TABLE TestTable AS
       SELECT generate_series AS id
       FROM generate_series(%d, %d)
       """ % (first_id, last_id))

class CollectionTest(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_make_table(self):
        store = get_store()
        make_table(store, 1, 4)
        result = store.find(TestTable)
        for res in result:
            print res.id


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

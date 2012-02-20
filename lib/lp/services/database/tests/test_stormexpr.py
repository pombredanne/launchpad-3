# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from storm.expr import (
    Column,
    compile,
    Select,
    SQLToken,
    State,
    )
from testtools import TestCase

from lp.services.database.stormexpr import BulkInsert


# Create columnN, tableN, and elemN variables.
for i in range(10):
    for name in ["column", "elem"]:
        exec "%s%d = SQLToken('%s%d')" % (name, i, name, i)
    for name in ["table"]:
        exec "%s%d = '%s %d'" % (name, i, name, i)


class TestBulkInsert(TestCase):

    def test_insert_bulk(self):
        expr = BulkInsert(
            (Column(column1, table1), Column(column2, table1)),
            expr=[(elem1, elem2), (elem3, elem4)])
        state = State()
        statement = compile(expr, state)
        self.assertEquals(
            statement,
            'INSERT INTO "table 1" (column1, column2) '
            'VALUES (elem1, elem2), (elem3, elem4)')
        self.assertEquals(state.parameters, [])

    def test_insert_select(self):
        expr = BulkInsert(
            (Column(column1, table1), Column(column2, table1)),
            expr=Select((Column(column3, table3), Column(column4, table4))))
        state = State()
        statement = compile(expr, state)
        self.assertEquals(
            statement,
            'INSERT INTO "table 1" (column1, column2) '
            '(SELECT "table 3".column3, "table 4".column4 '
            'FROM "table 3", "table 4")')
        self.assertEquals(state.parameters, [])

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'BulkInsert',
    'Concatenate',
    'CountDistinct',
    'Greatest',
    ]

from storm.expr import (
    BinaryOper,
    build_tables,
    COLUMN_NAME,
    compile,
    EXPR,
    Expr,
    NamedFunc,
    TABLE,
    Undef,
    )


class Greatest(NamedFunc):
    # XXX wallyworld 2011-01-31 bug=710466:
    # We need to use a Postgres greatest() function call but Storm
    # doesn't support that yet.
    __slots__ = ()
    name = "GREATEST"


class CountDistinct(Expr):
    # XXX: wallyworld 2010-11-26 bug=675377:
    # storm's Count() implementation is broken for distinct with > 1
    # column.

    __slots__ = ("columns")

    def __init__(self, columns):
        self.columns = columns


@compile.when(CountDistinct)
def compile_countdistinct(compile, countselect, state):
    state.push("context", EXPR)
    col = compile(countselect.columns)
    state.pop()
    return "count(distinct(%s))" % col


class Concatenate(BinaryOper):
    """Storm operator for string concatenation."""
    __slots__ = ()
    oper = " || "


class BulkInsert(Expr):
    """Expression representing an insert statement.

    This is storm.expr.Insert from lp:~wgrant/launchpad/bulk-insert, which is
    not yet approved.

    @ivar map: Dictionary mapping columns to values, or a sequence of columns
        for a bulk insert.
    @ivar table: Table where the row should be inserted.
    @ivar default_table: Table to use if no table is explicitly provided, and
        no tables may be inferred from provided columns.
    @ivar primary_columns: Tuple of columns forming the primary key of the
        table where the row will be inserted.  This is a hint used by backends
        to process the insertion of rows.
    @ivar primary_variables: Tuple of variables with values for the primary
        key of the table where the row will be inserted.  This is a hint used
        by backends to process the insertion of rows.
    @ivar expr: Expression or sequence of tuples of values for bulk insertion.
    """
    __slots__ = ("map", "table", "default_table", "primary_columns",
                 "primary_variables", "expr")

    def __init__(self, map, table=Undef, default_table=Undef,
                 primary_columns=Undef, primary_variables=Undef,
                 expr=Undef):
        self.map = map
        self.table = table
        self.default_table = default_table
        self.primary_columns = primary_columns
        self.primary_variables = primary_variables
        self.expr = expr


@compile.when(BulkInsert)
def compile_bulkinsert(compile, insert, state):
    state.push("context", COLUMN_NAME)
    columns = compile(tuple(insert.map), state, token=True)
    state.context = TABLE
    table = build_tables(compile, insert.table, insert.default_table, state)
    state.context = EXPR
    expr = insert.expr
    if expr is Undef:
        expr = [tuple(insert.map.itervalues())]
    if isinstance(expr, Expr):
        compiled_expr = compile(expr, state)
    else:
        compiled_expr = (
            "VALUES (%s)" %
            "), (".join(compile(values, state) for values in expr))
    state.pop()
    return "".join(
        ["INSERT INTO ", table, " (", columns, ") ", compiled_expr])

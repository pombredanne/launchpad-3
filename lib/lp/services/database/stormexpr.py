# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'AdvisoryUnlock',
    'Array',
    'Concatenate',
    'CountDistinct',
    'Greatest',
    'NullCount',
    'TryAdvisoryLock',
    ]

from storm.expr import (
    BinaryOper,
    ComparableExpr,
    compile,
    EXPR,
    Expr,
    NamedFunc,
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


class NullCount(NamedFunc):
    __slots__ = ()
    name = "NULL_COUNT"


class Array(ComparableExpr):
    __slots__ = ("args",)

    def __init__(self, *args):
        self.args = args


class TryAdvisoryLock(NamedFunc):

    __slots__ = ()

    name = 'PG_TRY_ADVISORY_LOCK'


class AdvisoryUnlock(NamedFunc):

    __slots__ = ()

    name = 'PG_ADVISORY_UNLOCK'


@compile.when(Array)
def compile_array(compile, array, state):
    state.push("context", EXPR)
    args = compile(array.args, state)
    state.pop()
    return "ARRAY[%s]" % args

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Operators and functions for Storm queries that are not in Storm.

You can use these to do FTI queries like this:

    >>> search_vector_column = <table.column>
    >>> query_function = FTQ(search_term)
    >>> rank = RANK(search_vector_column, query_function)
    >>> select_spec = <required_columns, rank>
    >>> results = store.find(
    ...     (select_spec),
    ...     Match(search_vector_column, query_function))
    >>> results.order_by(Desc(rank))

"""

__metaclass__ = type

__all__ = [
    'FTQ',
    'Match',
    'RANK',
    ]

from storm.expr import (
    CompoundOper,
    NamedFunc,
    )


class FTQ(NamedFunc):
    """Full Text Query function.

    Implements the PostgreSQL ftq() function: ftq(search_string)
    Returns a ts_query
    """
    __slots__ = ()
    name = "FTQ"


class RANK(NamedFunc):
    """Full text rank function.

    Implements the PostgreSQL ts_rank() function:
    ts_rank(
        [ weights float4[], ]
        vector tsvector,
        query tsquery [,
        normalization integer ])

    Returns a float4.
    """
    __slots__ = ()
    name = "TS_RANK"


class Match(CompoundOper):
    """Full text match operator.

    The full text match operator is used to compare a compiled search
    (tsquery) expression to a text search vector (tsvector). In PostgreSQL, the
    operator returns a "true" value if the tsvector matches the tsquery.
    """
    __slots__ = ()
    oper = "@@"


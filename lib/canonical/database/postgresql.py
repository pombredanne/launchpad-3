# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
PostgreSQL specific helper functions, such as database introspection
and table manipulation

XXX: Work in progress -- StuartBishop 2005-03-07
"""

__metaclass__ = type

def queryReferences(cur, table, column, _state=None):
    """Return a list of all foreign key references to the given table column

    `table` and `column` are both case sensitive strings (so they should
    usually be lowercase strings as per PostgreSQL default behavior).
    
    `cur` is an open DB-API cursor

    returns `[(from_table, from_column, to_table, to_column, update, delete)]`

    `from` entries refer to the `to` entries. This method is recursive -
    not only does it return all references to the given table column, but
    also all references to those references etc. (indirect references).

    `update` is the update clause (eg. on update cascade)
    `delete` is the delete clause (eg. on delete cascade)

    Entries are returned in order traversed, so with care this can be used
    to change keys.

    >>> for r in queryReferences(cur, 'a', 'aid'):
    ...     print repr(r)
    ('a', 'selfref', 'a', 'aid', u'a', u'a')
    ('b', 'aid', 'a', 'aid', u'c', u'c')
    ('c', 'aid', 'b', 'aid', u'a', u'a')
    ('d', 'aid', 'b', 'aid', u'a', u'a')

    Of course, there might not be any references

    >>> queryReferences(cur, 'a', 'selfref')
    []

    """

    sql = """
        SELECT DISTINCT
            src_pg_class.relname AS srctable,
            src_pg_attribute.attname AS srccol,
            ref_pg_class.relname AS reftable,
            ref_pg_attribute.attname AS refcol,
            pg_constraint.confupdtype,
            pg_constraint.confdeltype
        FROM
            pg_constraint
                JOIN pg_class AS src_pg_class
                    ON src_pg_class.oid = pg_constraint.conrelid
                JOIN pg_class AS ref_pg_class
                    ON ref_pg_class.oid = pg_constraint.confrelid
                JOIN pg_attribute AS src_pg_attribute
                    ON src_pg_class.oid = src_pg_attribute.attrelid
                JOIN pg_attribute AS ref_pg_attribute
                    ON ref_pg_class.oid = ref_pg_attribute.attrelid,
            information_schema._pg_keypositions() pos(n)
        WHERE
            contype = 'f'
            AND ref_pg_class.relname = %(table)s
            AND ref_pg_attribute.attname = %(column)s
            AND src_pg_attribute.attnum = pg_constraint.conkey[n]
            AND ref_pg_attribute.attnum = pg_constraint.confkey[n]
            AND NOT src_pg_attribute.attisdropped
            AND NOT ref_pg_attribute.attisdropped
        ORDER BY src_pg_class.relname, src_pg_attribute.attname
        """
    cur.execute(sql, vars())

    # Recursive function. Create the list that stores our state.
    # We pass this down to subinvocations to avoid loops.
    if _state is None:
        _state = []

    for t in cur.fetchall():
        # t == (src_table, src_column, dest_table, dest_column, upd, del)
        if t not in _state: # Avoid loops
            _state.append(t)
            # Recurse, Locating references to the reference we just found.
            queryReferences(cur, t[0], t[1], _state)
    # Don't sort. This way, we return the columns in order of distance
    # from the original (table, column), making it easier to change keys
    return _state

def queryUniques(cur, table, column):
    '''Return a list of unique indexes on `table` that include the `column`

    `cur` must be an open DB-API cursor.

    Returns [ (column, [...]) ]. The column passed in will always be
    included in the tuple.

    Simple UNIQUE index

    >>> queryUniques(cur, 'b', 'aid')
    [('aid',)]

    Primary keys are UNIQUE indexes too

    >>> queryUniques(cur, 'a', 'aid')
    [('aid',)]

    Compound indexes

    >>> queryUniques(cur, 'c', 'aid')
    [('aid', 'bid')]
    >>> queryUniques(cur, 'c', 'bid')
    [('aid', 'bid')]

    And any combination

    >>> l = queryUniques(cur, 'd', 'aid')
    >>> l.sort()
    >>> l
    [('aid',), ('aid', 'bid')]

    If there are no UNIQUE indexes using the secified column

    >>> queryUniques(cur, 'a', 'selfref')
    []

    '''

    # Retrieve the attributes for the table
    attributes = {}
    sql = '''
        SELECT
            a.attnum,
            a.attname
        FROM
            pg_class AS t JOIN pg_attribute AS a ON t.oid = a.attrelid
        WHERE
            t.relname = %(table)s
            AND a.attnum > 0
        '''
    cur.execute(sql, vars())
    for num,name in cur.fetchall():
        attributes[int(num)] = name

    # Initialize our return value
    rv = []

    # Retrive the UNIQUE indexes. 
    sql = '''
        SELECT
            i.indkey
        FROM
            pg_class AS t JOIN pg_index AS i ON i.indrelid = t.oid
        WHERE
            i.indisunique = true
            AND t.relname = %(table)s
        '''
    cur.execute(sql, vars())
    for indkey, in cur.fetchall():
        # We have a space seperated list of integer keys into the attribute
        # mapping
        keys = [attributes[int(key)] for key in indkey.split()]
        if column in keys:
            rv.append(tuple(keys))
    return rv


if __name__ == '__main__':
    import psycopg
    con = psycopg.connect('dbname=launchpad_dev user=launchpad')
    cur = con.cursor()
    
    for table, column in queryReferences(cur, 'person', 'id'):
        print '%32s %32s' % (table, column)

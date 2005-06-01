# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
PostgreSQL specific helper functions, such as database introspection
and table manipulation
"""

__metaclass__ = type

import re

from sqlbase import quote, quoteIdentifier, cursor

def listReferences(cur, table, column, _state=None):
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

    >>> for r in listReferences(cur, 'a', 'aid'):
    ...     print repr(r)
    ('a', 'selfref', 'a', 'aid', u'a', u'a')
    ('b', 'aid', 'a', 'aid', u'c', u'c')
    ('c', 'aid', 'b', 'aid', u'a', u'a')
    ('d', 'aid', 'b', 'aid', u'a', u'a')

    Of course, there might not be any references

    >>> listReferences(cur, 'a', 'selfref')
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
            listReferences(cur, t[0], t[1], _state)
    # Don't sort. This way, we return the columns in order of distance
    # from the original (table, column), making it easier to change keys
    return _state

def listUniques(cur, table, column):
    '''Return a list of unique indexes on `table` that include the `column`

    `cur` must be an open DB-API cursor.

    Returns [ (column, [...]) ]. The column passed in will always be
    included in the tuple.

    Simple UNIQUE index

    >>> listUniques(cur, 'b', 'aid')
    [('aid',)]

    Primary keys are UNIQUE indexes too

    >>> listUniques(cur, 'a', 'aid')
    [('aid',)]

    Compound indexes

    >>> listUniques(cur, 'c', 'aid')
    [('aid', 'bid')]
    >>> listUniques(cur, 'c', 'bid')
    [('aid', 'bid')]

    And any combination

    >>> l = listUniques(cur, 'd', 'aid')
    >>> l.sort()
    >>> l
    [('aid',), ('aid', 'bid')]

    If there are no UNIQUE indexes using the secified column

    >>> listUniques(cur, 'a', 'selfref')
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

def listSequences(cur):
    """Return a list of (schema, sequence, table, column) tuples.

    `table` and `column` refer to the column that appears to be automatically
    populated from the sequence. They will be None if this sequence is
    standalone.

    >>> for r in listSequences(cur):
    ...     print repr(r)
    ('public', 'a_aid_seq', 'a', 'aid')
    ('public', 'standalone', None, None)

    """
    sql = """
        SELECT
            n.nspname AS schema,
            c.relname AS seqname
        FROM
            pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE
            c.relkind = 'S'
            AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
            AND pg_table_is_visible(c.oid)
        ORDER BY schema, seqname
        """
    rv = []
    cur.execute(sql)
    for schema, sequence in list(cur.fetchall()):
        match = re.search('^(\w+)_(\w+)_seq$', sequence)
        if match is None:
            rv.append( (schema, sequence, None, None) )
        else:
            table = match.group(1)
            column = match.group(2)
            sql = """
                SELECT count(*)
                FROM
                    pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    JOIN pg_attribute a ON c.oid = a.attrelid
                WHERE
                    a.attnum > 0 AND NOT a.attisdropped
                    AND n.nspname = %(schema)s
                    AND c.relname = %(table)s
                    AND a.attname = %(column)s
                """
            cur.execute(sql, vars())
            num = cur.fetchone()[0]
            if num == 1:
                rv.append( (schema, sequence, table, column) )
            else:
                rv.append( (schema, sequence, None, None) )
    return rv

def resetSequences(cur):
    """Reset table sequences to match the data in them.
    
    Goes through the database resetting the values of sequences to match
    what is in their corresponding tables, where corresponding tables are
    known.

    >>> cur.execute("SELECT nextval('a_aid_seq')")
    >>> int(cur.fetchone()[0])
    1
    >>> cur.execute("SELECT nextval('a_aid_seq')")
    >>> cur.execute("SELECT nextval('a_aid_seq')")
    >>> resetSequences(cur)
    >>> cur.execute("SELECT nextval('a_aid_seq')")
    >>> int(cur.fetchone()[0])
    1
    """
    for schema, sequence, table, column in listSequences(cur):
        if table is None or column is None:
            continue
        sql = "SELECT max(%s) FROM %s" % (
                quoteIdentifier(column), quoteIdentifier(table)
                )
        cur.execute(sql)
        last_value = cur.fetchone()[0]
        if last_value is None:
            last_value = 1
            flag = 'false'
        else:
            flag = 'true'
        sql = "SELECT setval(%s, %d, %s)" % (
                quote('%s.%s' % (schema, sequence)), int(last_value), flag
                )
        cur.execute(sql)

if __name__ == '__main__':
    import psycopg
    con = psycopg.connect('dbname=launchpad_dev user=launchpad')
    cur = con.cursor()
    
    for table, column in listReferences(cur, 'person', 'id'):
        print '%32s %32s' % (table, column)

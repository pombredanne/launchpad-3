#!/usr/bin/env python
'''
Add full text indexes to the launchpad database
'''

import sys, os.path, os
sys.path.append(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'lib',
    ))

import psycopg, popen2, re
from optparse import OptionParser
from canonical.lp import dbname, dbhost

# Defines parser and locale to use.
DEFAULT_CONFIG = 'default'
TSEARCH2_SQL = '/usr/share/postgresql/contrib/tsearch2.sql'
PATCH_SQL = os.path.join(
        os.path.dirname(__file__), 'regprocedure_update.sql'
        )

ALL_FTI = [
    ('bug', ['name', 'title', 'shortdesc', 'description']),
    ('message', ['title', 'contents']),
    ('person', ['givenname', 'familyname', 'displayname']),
    ('product', ['name', 'displayname', 'title', 'shortdesc', 'description']),
    ('project', ['name', 'displayname', 'title', 'shortdesc', 'description']),
    ('sourcepackage', ['shortdesc', 'description']),
    ('binarypackage', ['shortdesc', 'description']),
    ]

def quote_identifier(identifier):
    '''Quote an identifier like a table name or column name'''
    quote_dict = {'\"': '""', "\\": "\\\\"}
    for dkey in quote_dict.keys():
        if identifier.find(dkey) >= 0:
            identifier=quote_dict[dkey].join(identifier.split(dkey))
    return '"%s"' % identifier

def execute(con, sql):
    sql = sql.strip()
    if options.verbose > 1:
        print '* %s' % sql
    con.cursor().execute(sql)

def fti(con, table, columns, configuration=DEFAULT_CONFIG):
    '''Setup full text indexing for a table'''

    index = quote_identifier("%s_fti" % table)
    table = quote_identifier(table)
    columns = [quote_identifier(c) for c in columns]

    # Drop the trigger if it exists
    try:
        execute(con, "DROP TRIGGER tsvectorupdate ON %s" % table)
        con.commit()
    except psycopg.ProgrammingError:
        con.rollback()

    # Drop the fti index if it exists
    try:
        execute(con, "DROP INDEX %s" % index)
        con.commit()
    except psycopg.ProgrammingError:
        con.rollback()

    # Create the 'fti' column if it doesn't already exist
    try:
        execute(con, "SELECT fti FROM %s LIMIT 1" % table)
    except psycopg.ProgrammingError:
        con.rollback()
        execute(con, "ALTER TABLE %s ADD COLUMN fti tsvector" % table)

    # Rebuild the fti column, as its columns or configuration may have changed
    coalesces = " || ' ' || ".join(["coalesce(%s,'')" % c for c in columns])
    sql = "UPDATE %s SET fti=to_tsvector(%s,%s)" % (
            table, psycopg.QuotedString(configuration), coalesces
            )
    execute(con, sql)

    # Create the fti index
    execute(con, "CREATE INDEX %s ON %s USING gist(fti)" % (
        index, table
        ))

    # Create the trigger
    sql = """
        CREATE TRIGGER tsvectorupdate BEFORE UPDATE OR INSERT ON %s
        FOR EACH ROW EXECUTE PROCEDURE tsearch2(fti, %s)
        """ % (table, ', '.join(columns))
    execute(con, sql)
    con.commit()

def setup(con, configuration=DEFAULT_CONFIG):
    """Setup and install tsearch2 if isn't already"""
    try:
        execute(con, 'SET search_path = ts2, public;')
    except psycopg.ProgrammingError:
        con.rollback()
        execute(con, 'CREATE SCHEMA ts2')
        execute(con, 'SET search_path = ts2, public;')
        con.commit()

    try:
        execute(con, 'SELECT * from pg_ts_cfg')
        if options.verbose:
            print '* tsearch2 already installed'
    except psycopg.ProgrammingError:
        con.rollback()
        if options.verbose:
            print '* Installing tsearch2'
        if dbhost:
            cmd = 'psql -d %s -h %s -f -' % (dbname, dbhost)
        else:
            cmd = 'psql -d %s -f -' % (dbname,)
        p = popen2.Popen4(cmd)
        c = p.tochild
        print >> c, "SET client_min_messages=ERROR;"
        print >> c, "CREATE SCHEMA ts2;"
        print >> c, open(TSEARCH2_SQL).read().replace('public;','ts2, public;')
        print >> c, open(PATCH_SQL).read()
        p.tochild.close()
        rv = p.wait()
        if rv != 0:
            print '* Error executing %s:' % cmd
            print '---'
            print p.fromchild.read()
            print '---'
            sys.exit(rv)

    # Create ftq helper
    execute(con, r"""
        CREATE OR REPLACE FUNCTION ftq(text) RETURNS tsquery AS '
            import re
            q = args[0].lower()
            q = re.subn("[\|\&]", " ", q)
            q = "|".join(args[0].lower().split())
            p = plpy.prepare("SELECT to_tsquery(\'%s\', $1) AS x", ["text"])
            q = plpy.execute(p, [q], 1)[0]["x"]
            return q or None
        ' LANGUAGE plpythonu
        """ % configuration)

    execute(con,
            r"COMMENT ON FUNCTION ftq(text) IS '"
            r"Convert a string to a tsearch2 query using the preferred "
            r"configuration. eg. "
            r""""SELECT * FROM Bug WHERE fti @@ ftq(''fatal crash'')". """
            r"The query is lowercased, and multiple words searched using OR.'"
            )

    con.commit()

    # Don't bother with this - the setting is not exported with dumps
    # or propogated  when duplicating the database. Only reliable
    # way we can use is setting search_path in postgresql.conf
    #
    # Set the default schema search path so this stuff can be found
    #execute(con, 'ALTER DATABASE %s SET search_path = public,ts2;' % dbname)
    #con.commit()

def main():
    if options.verbose:
        print "* Connecting to dbname='%s' host='%s'" % (dbname, dbhost)
    if dbhost:
        con = psycopg.connect('dbname=%s host=%s' % (dbname, dbhost))
    else:
        con = psycopg.connect('dbname=%s' % (dbname,))
    setup(con)
    if not options.setup:
        for row in ALL_FTI:
            fti(con, *row)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option(
            "-v", "--verbose", dest="verbose",
            action="count", default=0,
            help="Verbose",
            )
    parser.add_option(
            "-s", "--setup-only", dest="setup",
            action="store_true", default=False,
            help="Only install tsearch2 - don't build the indexes",
            )
    (options, args) = parser.parse_args()
    main()


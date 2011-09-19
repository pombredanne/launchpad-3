#!/usr/bin/python -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# This modules uses relative imports.
# pylint: disable-msg=W0403

"""
Add full text indexes to the launchpad database
"""
__metaclass__ = type

from distutils.version import LooseVersion
from optparse import OptionParser
import os.path
import subprocess
import sys
from tempfile import NamedTemporaryFile
from textwrap import dedent
import time

import _pythonpath
import psycopg2.extensions
import replication.helpers

from canonical.config import config
from canonical.database.postgresql import ConnectionString
from canonical.database.sqlbase import (
    connect,
    ISOLATION_LEVEL_AUTOCOMMIT,
    ISOLATION_LEVEL_READ_COMMITTED,
    quote,
    quote_identifier,
    )
from canonical.launchpad.scripts import (
    db_options,
    logger,
    logger_options,
    )

# Defines parser and locale to use.
DEFAULT_CONFIG = 'default'

PGSQL_BASE = '/usr/share/postgresql'

# tsearch2 ranking constants:
A, B, C, D = 'ABCD'

# This data structure defines all of our full text indexes.  Each tuple in the
# top level list creates a 'fti' column in the specified table.
# The letters letters A-D assign a weight to the corresponding column.
# A is most important, and D is least important. This affects result ordering
# when you are ordering by rank.
ALL_FTI = [
    ('archive', [
            ('description', A),
            ('package_description_cache', B),
            ]),
    ('bug', [
            ('name', A),
            ('title', B),
            ('description', D),
            ]),

    ('bugtask', [
            ('targetnamecache', B),
            ('statusexplanation', C),
            ]),

    ('binarypackagerelease', [
            ('summary', B),
            ('description', C),
            ]),

    ('cve', [
            ('sequence', A),
            ('description', B),
            ]),

    ('distribution', [
            ('name', A),
            ('displayname', A),
            ('title', B),
            ('summary', C),
            ('description', D),
            ]),

    ('distributionsourcepackagecache', [
            ('name', A),
            ('binpkgnames', B),
            ('binpkgsummaries', C),
            ('binpkgdescriptions', D),
            ('changelog', D),
            ]),

    ('distroseriespackagecache', [
            ('name', A),
            ('summaries', B),
            ('descriptions', C),
            ]),

    ('faq', [
            ('title', A),
            ('tags', B),
            ('content', D),
            ]),

    ('message', [
            ('subject', B),
            ]),

    ('messagechunk', [
            ('content', C),
            ]),

    ('person', [
            ('name', A),
            ('displayname', A),
            ]),

    ('product', [
            ('name', A),
            ('displayname', A),
            ('title', B),
            ('summary', C),
            ('description', D),
            ]),

    ('productreleasefile', [
            ('description', D),
            ]),

    ('project', [
            ('name', A),
            ('displayname', A),
            ('title', B),
            ('summary', C),
            ('description', D),
            ]),

    ('shippingrequest', [
            ('recipientdisplayname', A),
            ]),

    ('specification', [
            ('name', A),
            ('title', A),
            ('summary', B),
            ('whiteboard', D),
            ]),

    ('question', [
            ('title', A),
            ('description', B),
            ('whiteboard', B),
            ])
    ]


def execute(con, sql, results=False, args=None):
    sql = sql.strip()
    log.debug('* %s' % sql)
    cur = con.cursor()
    if args is None:
        cur.execute(sql)
    else:
        cur.execute(sql, args)
    if results:
        return list(cur.fetchall())
    else:
        return None


def sexecute(con, sql):
    """If we are generating a slonik script, write out the SQL to our
    SQL script. Otherwise execute on the DB.
    """
    if slonik_sql is not None:
        print >> slonik_sql, dedent(sql + ';')
    else:
        execute(con, sql)


def fti(con, table, columns, configuration=DEFAULT_CONFIG):
    """Setup full text indexing for a table"""

    index = "%s_fti" % table
    qindex = quote_identifier(index)
    qtable = quote_identifier(table)
    # Quote the columns
    qcolumns = [
        (quote_identifier(column), weight) for column, weight in columns
        ]

    # Drop the trigger if it exists
    trigger_exists = bool(execute(con, """
        SELECT COUNT(*) FROM pg_trigger, pg_class, pg_namespace
        WHERE pg_trigger.tgname = 'tsvectorupdate'
            AND pg_trigger.tgrelid = pg_class.oid
            AND pg_class.relname = %(table)s
            AND pg_class.relnamespace = pg_namespace.oid
            AND pg_namespace.nspname = 'public'
        """, results=True, args=vars())[0][0])
    if trigger_exists:
        log.debug('tsvectorupdate trigger exists in %s. Dropping.' % qtable)
        sexecute(con, "DROP TRIGGER tsvectorupdate ON %s" % qtable)

    # Drop the fti index if it exists
    index_exists = bool(execute(con, """
        SELECT COUNT(*) FROM pg_index, pg_class, pg_namespace
        WHERE pg_index.indexrelid = pg_class.oid
            AND pg_class.relnamespace = pg_namespace.oid
            AND pg_class.relname = %(index)s
            AND pg_namespace.nspname = 'public'
        """, results=True, args=vars())[0][0])
    if index_exists:
        log.debug('%s exists. Dropping.' % qindex)
        sexecute(con, "DROP INDEX %s" % qindex)

    # Create the 'fti' column if it doesn't already exist
    column_exists = bool(execute(con, """
        SELECT COUNT(*) FROM pg_attribute, pg_class, pg_namespace
        WHERE pg_attribute.attname='fti'
            AND pg_attribute.attisdropped IS FALSE
            AND pg_attribute.attrelid = pg_class.oid
            AND pg_class.relname = %(table)s
            AND pg_class.relnamespace = pg_namespace.oid
            AND pg_namespace.nspname = 'public'
        """, results=True, args=vars())[0][0])
    if not column_exists:
        log.debug('fti column does not exist in %s. Creating.' % qtable)
        sexecute(con, "ALTER TABLE %s ADD COLUMN fti tsvector" % qtable)

    # Create the trigger
    columns_and_weights = []
    for column, weight in qcolumns:
        columns_and_weights.extend((column, weight))

    sql = """
        CREATE TRIGGER tsvectorupdate BEFORE UPDATE OR INSERT ON %s
        FOR EACH ROW EXECUTE PROCEDURE ftiupdate(%s)
        """ % (table, ','.join(columns_and_weights))
    sexecute(con, sql)

    # Rebuild the fti column, as the information it contains may be out
    # of date with recent configuration updates.
    sexecute(con, r"""UPDATE %s SET fti=NULL""" % qtable)

    # Create the fti index
    sexecute(con, "CREATE INDEX %s ON %s USING gist(fti)" % (
        qindex, qtable
        ))


def nullify(con):
    """Set all fti index columns to NULL"""
    for table, ignored in ALL_FTI:
        table = quote_identifier(table)
        log.info("Removing full text index data from %s", table)
        sexecute(con, "ALTER TABLE %s DISABLE TRIGGER tsvectorupdate" % table)
        sexecute(con, "UPDATE %s SET fti=NULL" % table)
        sexecute(con, "ALTER TABLE %s ENABLE TRIGGER tsvectorupdate" % table)
    sexecute(con, "DELETE FROM FtiCache")


def liverebuild(con):
    """Rebuild the data in all the fti columns against possibly live database.
    """
    # Update number of rows per transaction.
    batch_size = 50

    cur = con.cursor()
    for table, ignored in ALL_FTI:
        table = quote_identifier(table)
        cur.execute("SELECT max(id) FROM %s" % table)
        max_id = cur.fetchone()[0]
        if max_id is None:
            log.info("No data in %s - skipping", table)
            continue

        log.info("Rebuilding fti column on %s", table)
        for id in range(0, max_id, batch_size):
            try:
                query = """
                    UPDATE %s SET fti=NULL WHERE id BETWEEN %d AND %d
                    """ % (table, id + 1, id + batch_size)
                log.debug(query)
                cur.execute(query)
            except psycopg2.Error:
                # No commit - we are in autocommit mode
                log.exception('psycopg error')
                con = connect()
                con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)


def setup(con, configuration=DEFAULT_CONFIG):
    """Setup and install tsearch2 if isn't already"""

    # tsearch2 is out-of-the-box in 8.3+
    required = LooseVersion('8.3.0')
    assert get_pgversion(con) >= required, (
        'This script only supports PostgreSQL 8.3+')

    schema_exists = bool(execute(
        con, "SELECT COUNT(*) FROM pg_namespace WHERE nspname='ts2'",
        results=True)[0][0])
    if not schema_exists:
        execute(con, 'CREATE SCHEMA ts2')
        con.commit()
    execute(con, 'SET search_path = ts2, public;')

    tsearch2_sql_path = get_tsearch2_sql_path(con)

    ts2_installed = bool(execute(con, """
        SELECT COUNT(*) FROM pg_type,pg_namespace
        WHERE pg_type.typnamespace=pg_namespace.oid
            AND pg_namespace.nspname  = 'ts2'
        """, results=True)[0][0])
    if not ts2_installed:
        assert slonik_sql is None, """
            tsearch2 needs to be setup on each node first with
            fti.py --setup-only
            """

        log.debug('Installing tsearch2')
        cmd = 'psql -f - %s' % ConnectionString(
            config.database.rw_main_master).asPGCommandLineArgs()
        p = subprocess.Popen(
            cmd.split(' '), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        tsearch2_sql = open(tsearch2_sql_path).read()
        out, err = p.communicate(
            "SET client_min_messages=ERROR; CREATE SCHEMA ts2;" +
            tsearch2_sql.replace('public;', 'ts2, public;'))
        if p.returncode != 0:
            log.fatal("Error executing %s:", cmd)
            log.debug(out)
            sys.exit(p.returncode)

    # Create ftq helper and its sibling _ftq.
    # ftq(text) returns a tsquery, suitable for use querying the full text
    # indexes. _ftq(text) returns the string that would be parsed by
    # to_tsquery and is used to debug the query we generate.
    shared_func = r'''
        import re

        # I think this method would be more robust if we used a real
        # tokenizer and parser to generate the query string, but we need
        # something suitable for use as a stored procedure which currently
        # means no external dependancies.

        # Convert to Unicode
        query = args[0].decode('utf8')
        ## plpy.debug('1 query is %s' % repr(query))

        # Normalize whitespace
        query = re.sub("(?u)\s+"," ", query)

        # Convert AND, OR, NOT and - to tsearch2 punctuation
        query = re.sub(r"(?u)(?:^|\s)-([\w\(])", r" !\1", query)
        query = re.sub(r"(?u)\bAND\b", "&", query)
        query = re.sub(r"(?u)\bOR\b", "|", query)
        query = re.sub(r"(?u)\bNOT\b", " !", query)
        ## plpy.debug('2 query is %s' % repr(query))

        # Deal with unwanted punctuation. We convert strings of punctuation
        # inside words to a '-' character for the hypenation handling below
        # to deal with further. Outside of words we replace with whitespace.
        # We don't mess with -&|!()' as they are handled later.
        #punctuation = re.escape(r'`~@#$%^*+=[]{}:;"<>,.?\/')
        punctuation = r"[^\w\s\-\&\|\!\(\)']"
        query = re.sub(r"(?u)(\w)%s+(\w)" % (punctuation,), r"\1-\2", query)
        query = re.sub(r"(?u)%s+" % (punctuation,), " ", query)
        ## plpy.debug('3 query is %s' % repr(query))

        # Strip ! characters inside and at the end of a word
        query = re.sub(r"(?u)(?<=\w)[\!]+", " ", query)

        # Now that we have handled case-sensitive booleans, convert to
        # lowercase.
        query = query.lower()

        # Convert foo-bar to ((foo&bar)|foobar) and foo-bar-baz to
        # ((foo&bar&baz)|foobarbaz)
        def hyphen_repl(match):
            bits = match.group(0).split("-")
            return "((%s)|%s)" % ("&".join(bits), "".join(bits))
        query = re.sub(r"(?u)\b\w+-[\w\-]+\b", hyphen_repl, query)
        ## plpy.debug('4 query is %s' % repr(query))

        # Any remaining - characters are spurious
        query = query.replace('-','')

        # Remove unpartnered bracket on the left and right
        query = re.sub(r"(?ux) ^ ( [^(]* ) \)", r"(\1)", query)
        query = re.sub(r"(?ux) \( ( [^)]* ) $", r"(\1)", query)

        # Remove spurious brackets
        query = re.sub(r"(?u)\(([^\&\|]*?)\)", r" \1 ", query)
        ## plpy.debug('5 query is %s' % repr(query))

        # Insert & between tokens without an existing boolean operator
        # ( not proceeded by (|&!
        query = re.sub(r"(?u)(?<![\(\|\&\!])\s*\(", "&(", query)
        ## plpy.debug('6 query is %s' % repr(query))
        # ) not followed by )|&
        query = re.sub(r"(?u)\)(?!\s*(\)|\||\&|\s*$))", ")&", query)
        ## plpy.debug('6.1 query is %s' % repr(query))
        # Whitespace not proceded by (|&! not followed by &|
        query = re.sub(r"(?u)(?<![\(\|\&\!\s])\s+(?![\&\|\s])", "&", query)
        ## plpy.debug('7 query is %s' % repr(query))

        # Detect and repair syntax errors - we are lenient because
        # this input is generally from users.

        # Fix unbalanced brackets
        openings = query.count("(")
        closings = query.count(")")
        if openings > closings:
            query = query + " ) "*(openings-closings)
        elif closings > openings:
            query = " ( "*(closings-openings) + query
        ## plpy.debug('8 query is %s' % repr(query))

        # Strip ' character that do not have letters on both sides
        query = re.sub(r"(?u)((?<!\w)'|'(?!\w))", "", query)

        # Brackets containing nothing but whitespace and booleans, recursive
        last = ""
        while last != query:
            last = query
            query = re.sub(r"(?u)\([\s\&\|\!]*\)", "", query)
        ## plpy.debug('9 query is %s' % repr(query))

        # An & or | following a (
        query = re.sub(r"(?u)(?<=\()[\&\|\s]+", "", query)
        ## plpy.debug('10 query is %s' % repr(query))

        # An &, | or ! immediatly before a )
        query = re.sub(r"(?u)[\&\|\!\s]*[\&\|\!]+\s*(?=\))", "", query)
        ## plpy.debug('11 query is %s' % repr(query))

        # An &,| or ! followed by another boolean.
        query = re.sub(r"(?ux) \s* ( [\&\|\!] ) [\s\&\|]+", r"\1", query)
        ## plpy.debug('12 query is %s' % repr(query))

        # Leading & or |
        query = re.sub(r"(?u)^[\s\&\|]+", "", query)
        ## plpy.debug('13 query is %s' % repr(query))

        # Trailing &, | or !
        query = re.sub(r"(?u)[\&\|\!\s]+$", "", query)
        ## plpy.debug('14 query is %s' % repr(query))

        # If we have nothing but whitespace and tsearch2 operators,
        # return NULL.
        if re.search(r"(?u)^[\&\|\!\s\(\)]*$", query) is not None:
            return None

        # Convert back to UTF-8
        query = query.encode('utf8')
        ## plpy.debug('15 query is %s' % repr(query))
        '''
    text_func = shared_func + """
        return query or None
        """
    tsquery_func = shared_func + """
        p = plpy.prepare("SELECT to_tsquery('%s', $1) AS x", ["text"])
        query = plpy.execute(p, [query], 1)[0]["x"]
        return query or None
        """ % configuration
    sexecute(con, r"""
        CREATE OR REPLACE FUNCTION ts2._ftq(text) RETURNS text AS %s
        LANGUAGE plpythonu IMMUTABLE
        RETURNS NULL ON NULL INPUT
        """ % quote(text_func))
    #print psycopg2.extensions.QuotedString(text_func)
    sexecute(con, r"""
        CREATE OR REPLACE FUNCTION ts2.ftq(text) RETURNS tsquery AS %s
        LANGUAGE plpythonu IMMUTABLE
        RETURNS NULL ON NULL INPUT
        """ % quote(tsquery_func))

    sexecute(con,
            r"COMMENT ON FUNCTION ftq(text) IS '"
            r"Convert a string to a tsearch2 query using the preferred "
            r"configuration. eg. "
            r""""SELECT * FROM Bug WHERE fti @@ ftq(''fatal crash'')". """
            r"The query is lowercased, and multiple words searched using "
            r"AND.'"
            )
    sexecute(con,
            r"COMMENT ON FUNCTION ftq(text) IS '"
            r"Convert a string to an unparsed tsearch2 query'"
            )

    # Create our trigger function. The default one that ships with tsearch2
    # doesn't support weighting so we need our own. We remove safety belts
    # since we know we will be calling it correctly.
    sexecute(con, r"""
        CREATE OR REPLACE FUNCTION ts2.ftiupdate() RETURNS trigger AS '
            new = TD["new"]
            args = TD["args"][:]

            # Short circuit if none of the relevant columns have been
            # modified and fti is not being set to NULL (setting the fti
            # column to NULL is thus how we can force a rebuild of the fti
            # column).
            if TD["event"] == "UPDATE" and new["fti"] != None:
                old = TD["old"]
                relevant_modification = False
                for column_name in args[::2]:
                    if new[column_name] != old[column_name]:
                        relevant_modification = True
                        break
                if not relevant_modification:
                    return "OK"

            # Generate an SQL statement that turns the requested
            # column values into a weighted tsvector
            sql = []
            for i in range(0, len(args), 2):
                sql.append(
                        "ts2.setweight(ts2.to_tsvector(''default'', coalesce("
                        "substring(ltrim($%d) from 1 for 2500),'''')),"
                        "CAST($%d AS \\"char\\"))" % (i + 1, i + 2))
                args[i] = new[args[i]]

            sql = "SELECT %s AS fti" % "||".join(sql)

            # Execute and store in the fti column
            plan = plpy.prepare(sql, ["text", "char"] * (len(args)/2))
            new["fti"] = plpy.execute(plan, args, 1)[0]["fti"]

            # Tell PostgreSQL we have modified the data
            return "MODIFY"
        ' LANGUAGE plpythonu
        """)

    sexecute(con,
        r"COMMENT ON FUNCTION ftiupdate() IS 'Trigger function that keeps "
        r"the fti tsvector column up to date.'"
        )

    # Confirm database locale is valid, and set the 'default' tsearch2
    # configuration to use it.
    r = execute(con, r"""
            SELECT setting FROM pg_settings
            WHERE context='internal' AND name='lc_ctype'
            """, results=True)
    assert len(r) == 1, 'Unable to determine database locale'
    locale = r[0][0]
    assert locale.startswith('en_') or locale in ('C', 'en'), (
            "Non-english database locales are not supported with launchpad. "
            "Fresh initdb required."
            )
    r = locale.split('.', 1)
    if len(r) > 1:
        assert r[1].upper() in ("UTF8", "UTF-8"), \
                "Only UTF8 encodings supported. Fresh initdb required."
    else:
        assert len(r) == 1, 'Invalid database locale %s' % repr(locale)

    r = execute(con,
            "SELECT COUNT(*) FROM pg_ts_config WHERE cfgname='default'",
            results=True)
    if r[0][0] == 0:
        sexecute(con, """
            CREATE TEXT SEARCH CONFIGURATION ts2.default (
                COPY = pg_catalog.english)""")

    # Don't bother with this - the setting is not exported with dumps
    # or propogated  when duplicating the database. Only reliable
    # way we can use is setting search_path in postgresql.conf
    #
    # Set the default schema search path so this stuff can be found
    #execute(con, 'ALTER DATABASE %s SET search_path = public,ts2;' % dbname)


def needs_refresh(con, table, columns):
    '''Return true if the index needs to be rebuilt.

    We know this by looking in our cache to see what the previous
    definitions were, and the --force command line argument
    '''
    current_columns = repr(sorted(columns))

    existing = execute(
        con, "SELECT columns FROM FtiCache WHERE tablename=%(table)s",
        results=True, args=vars()
        )
    if len(existing) == 0:
        log.debug("No fticache for %(table)s" % vars())
        sexecute(con, """
            INSERT INTO FtiCache (tablename, columns) VALUES (%s, %s)
            """ % (quote(table), quote(current_columns)))
        return True

    if not options.force:
        previous_columns = existing[0][0]
        if current_columns == previous_columns:
            log.debug("FtiCache for %(table)s still valid" % vars())
            return False
        log.debug("Cache out of date - %s != %s" % (
            current_columns, previous_columns
            ))
    sexecute(con, """
        UPDATE FtiCache SET columns = %s
        WHERE tablename = %s
        """ % (quote(current_columns), quote(table)))

    return True


def get_pgversion(con):
    rows = execute(con, r"show server_version", results=True)
    return LooseVersion(rows[0][0])


def get_tsearch2_sql_path(con):
    major, minor = get_pgversion(con).version[:2]
    path = os.path.join(
        PGSQL_BASE, '%d.%d' % (major, minor), 'contrib', 'tsearch2.sql')
    assert os.path.exists(path), '%s does not exist' % path
    return path


# Script options and arguments parsed from the command line by main()
options = None
args = None

# Logger, setup by main()
log = None

# Files for output generated for slonik(1). None if not a Slony-I install.
slonik_sql = None


def main():
    parser = OptionParser()
    parser.add_option(
            "-s", "--setup-only", dest="setup",
            action="store_true", default=False,
            help="Only install tsearch2 - don't build the indexes.",
            )
    parser.add_option(
            "-f", "--force", dest="force",
            action="store_true", default=False,
            help="Force a rebuild of all full text indexes.",
            )
    parser.add_option(
            "-0", "--null", dest="null",
            action="store_true", default=False,
            help="Set all full text index column values to NULL.",
            )
    parser.add_option(
            "-l", "--live-rebuild", dest="liverebuild",
            action="store_true", default=False,
            help="Rebuild all the indexes against a live database.",
            )
    db_options(parser)
    logger_options(parser)

    global options, args
    (options, args) = parser.parse_args()

    if options.setup + options.force + options.null + options.liverebuild > 1:
        parser.error("Incompatible options")

    global log
    log = logger(options)

    con = connect()

    is_replicated_db = replication.helpers.slony_installed(con)

    if options.liverebuild and is_replicated_db:
        parser.error("--live-rebuild does not work with Slony-I install.")

    if is_replicated_db:
        global slonik_sql
        slonik_sql = NamedTemporaryFile(prefix="fti_sl", suffix=".sql")
        print >> slonik_sql, "-- Generated by %s %s" % (
                sys.argv[0], time.ctime())

    if options.liverebuild:
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        liverebuild(con)
    else:
        con.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        setup(con)
        if options.null:
            nullify(con)
        elif not options.setup:
            for table, columns in ALL_FTI:
                if needs_refresh(con, table, columns):
                    log.info("Rebuilding full text index on %s", table)
                    fti(con, table, columns)
                else:
                    log.info(
                        "No need to rebuild full text index on %s", table)

    if is_replicated_db:
        slonik_sql.flush()
        con.close()
        log.info("Executing generated SQL using slonik")
        if replication.helpers.execute_slonik("""
            execute script (
                set id=@lpmain_set,
                event node=@master_node,
                filename='%s');
            """ % slonik_sql.name, sync=0):
            return 0
        else:
            log.fatal("Failed to execute SQL in Slony-I environment.")
            return 1
    else:
        con.commit()
        return 0


if __name__ == '__main__':
    sys.exit(main())

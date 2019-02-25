-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Drop the tsearch2 extension and ts2 schema.
--
-- PostgreSQL 10 removes contrib/tsearch2.
--
-- From the extension only ts2.tsvector survives, as
-- public.ts2_tsvector. It's an alias for pg_catalog.tsvector, but we
-- can't change existing column types without table rewrites or catalog
-- hackery.
--
-- ts2.ftiupdate() and the ts2.default text search config move into
-- public.

ALTER EXTENSION tsearch2 DROP DOMAIN ts2.tsvector;
DROP EXTENSION tsearch2;

ALTER DOMAIN ts2.tsvector RENAME TO ts2_tsvector;
ALTER DOMAIN ts2.ts2_tsvector SET SCHEMA public;

ALTER TEXT SEARCH CONFIGURATION ts2.default SET SCHEMA public;

ALTER FUNCTION ts2.ftiupdate() SET SCHEMA public;

-- From launchpad-2209-00-0.sql, but without ts2 schema specifiers since it's
-- all in pg_catalog now.
CREATE OR REPLACE FUNCTION ftiupdate() RETURNS trigger
    LANGUAGE plpythonu
    AS $_$
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
                "setweight(to_tsvector('default', coalesce("
                "substring(ltrim($%d) from 1 for 2500),'')),"
                "CAST($%d AS \"char\"))" % (i + 1, i + 2))
        args[i] = new[args[i]]

    sql = "SELECT %s AS fti" % "||".join(sql)

    # Execute and store in the fti column
    plan = plpy.prepare(sql, ["text", "char"] * (len(args)/2))
    new["fti"] = plpy.execute(plan, args, 1)[0]["fti"]

    # Tell PostgreSQL we have modified the data
    return "MODIFY"
$_$;

DROP SCHEMA ts2;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 84, 0);

SET client_min_messages = ERROR;

-- Update functions for PostgreSQL 9.5 and 9.6 support, in addition to 9.3.


-- From 2209-00-0
CREATE OR REPLACE FUNCTION update_branch_name_cache() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    needs_update boolean := FALSE;
BEGIN
    IF TG_OP = 'INSERT' THEN
        needs_update := TRUE;
    ELSIF (NEW.owner_name IS NULL
        OR NEW.unique_name IS NULL
        OR OLD.owner_name <> NEW.owner_name
        OR OLD.unique_name <> NEW.unique_name
        OR ((NEW.target_suffix IS NULL) <> (OLD.target_suffix IS NULL))
        OR COALESCE(OLD.target_suffix, '') <> COALESCE(NEW.target_suffix, '')
        OR OLD.name <> NEW.name
        OR OLD.owner <> NEW.owner
        OR COALESCE(OLD.product, -1) <> COALESCE(NEW.product, -1)
        OR COALESCE(OLD.distroseries, -1) <> COALESCE(NEW.distroseries, -1)
        OR COALESCE(OLD.sourcepackagename, -1)
            <> COALESCE(NEW.sourcepackagename, -1)) THEN
        needs_update := TRUE;
    END IF;

    IF needs_update THEN
        SELECT
            Person.name AS owner_name,
            COALESCE(Product.name, SPN.name) AS target_suffix,
            '~' || Person.name || '/' || COALESCE(
                Product.name,
                Distribution.name || '/' || Distroseries.name
                    || '/' || SPN.name,
                '+junk') || '/' || NEW.name AS unique_name
        INTO NEW.owner_name, NEW.target_suffix, NEW.unique_name
        FROM Person
        LEFT OUTER JOIN DistroSeries ON NEW.distroseries = DistroSeries.id
        LEFT OUTER JOIN Product ON NEW.product = Product.id
        LEFT OUTER JOIN Distribution
            ON Distroseries.distribution = Distribution.id
        LEFT OUTER JOIN SourcepackageName AS SPN
            ON SPN.id = NEW.sourcepackagename
        WHERE Person.id = NEW.owner;
    END IF;

    RETURN NEW;
END;
$$;


-- From 2209-21-4
CREATE OR REPLACE FUNCTION update_database_disk_utilization() RETURNS void
    LANGUAGE sql SECURITY DEFINER
    SET search_path TO public
    AS $$
    INSERT INTO DatabaseDiskUtilization
    SELECT
        CURRENT_TIMESTAMP AT TIME ZONE 'UTC',
        namespace, name,
        sub_namespace, sub_name,
        kind,
        (namespace || '.' ||  name || COALESCE(
                '/' || sub_namespace || '.' || sub_name, '')) AS sort,
        (stat).table_len,
        (stat).tuple_count,
        (stat).tuple_len,
        (stat).tuple_percent,
        (stat).dead_tuple_count,
        (stat).dead_tuple_len,
        (stat).dead_tuple_percent,
        (stat).free_space,
        (stat).free_percent
    FROM (
        -- Tables
        SELECT
            pg_namespace.nspname AS namespace,
            pg_class.relname AS name,
            NULL AS sub_namespace,
            NULL AS sub_name,
            pg_class.relkind AS kind,
            pgstattuple(pg_class.oid) AS stat
        FROM pg_class, pg_namespace
        WHERE
            pg_class.relnamespace = pg_namespace.oid
            AND pg_class.relkind = 'r'
            AND pg_table_is_visible(pg_class.oid)

        UNION ALL
        
        -- Indexes
        SELECT
            pg_namespace_table.nspname AS namespace,
            pg_class_table.relname AS name,
            pg_namespace_index.nspname AS sub_namespace,
            pg_class_index.relname AS sub_name,
            pg_class_index.relkind AS kind,
            pgstattuple(pg_class_index.oid) AS stat
        FROM
            pg_namespace AS pg_namespace_table,
            pg_namespace AS pg_namespace_index,
            pg_class AS pg_class_table,
            pg_class AS pg_class_index,
            pg_index,
            pg_am
        WHERE
            pg_class_index.relkind = 'i'
            AND pg_am.amname <> 'gin' -- pgstattuple doesn't support GIN
            AND pg_table_is_visible(pg_class_table.oid)
            AND pg_class_index.relnamespace = pg_namespace_index.oid
            AND pg_class_table.relnamespace = pg_namespace_table.oid
            AND pg_class_index.relam = pg_am.oid
            AND pg_index.indexrelid = pg_class_index.oid
            AND pg_index.indrelid = pg_class_table.oid

        UNION ALL

        -- TOAST tables
        SELECT
            pg_namespace_table.nspname AS namespace,
            pg_class_table.relname AS name,
            pg_namespace_toast.nspname AS sub_namespace,
            pg_class_toast.relname AS sub_name,
            pg_class_toast.relkind AS kind,
            pgstattuple(pg_class_toast.oid) AS stat
        FROM
            pg_namespace AS pg_namespace_table,
            pg_namespace AS pg_namespace_toast,
            pg_class AS pg_class_table,
            pg_class AS pg_class_toast
        WHERE
            pg_class_toast.relnamespace = pg_namespace_toast.oid
            AND pg_table_is_visible(pg_class_table.oid)
            AND pg_class_table.relnamespace = pg_namespace_table.oid
            AND pg_class_toast.oid = pg_class_table.reltoastrelid

        UNION ALL

        -- TOAST indexes
        SELECT
            pg_namespace_table.nspname AS namespace,
            pg_class_table.relname AS name,
            pg_namespace_index.nspname AS sub_namespace,
            pg_class_index.relname AS sub_name,
            pg_class_index.relkind AS kind,
            pgstattuple(pg_class_index.oid) AS stat
        FROM
            pg_namespace AS pg_namespace_table,
            pg_namespace AS pg_namespace_index,
            pg_class AS pg_class_table,
            pg_class AS pg_class_index,
            pg_class AS pg_class_toast,
            pg_index
        WHERE
            pg_class_table.relnamespace = pg_namespace_table.oid
            AND pg_table_is_visible(pg_class_table.oid)
            AND pg_class_index.relnamespace = pg_namespace_index.oid
            AND pg_class_table.reltoastrelid = pg_class_toast.oid
            AND pg_class_index.oid = pg_index.indexrelid
            AND pg_index.indrelid = pg_class_toast.oid
        ) AS whatever;
$$;


-- From 2209-24-3
CREATE OR REPLACE FUNCTION _ftq(text) RETURNS text
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $_$
        import re

        # I think this method would be more robust if we used a real
        # tokenizer and parser to generate the query string, but we need
        # something suitable for use as a stored procedure which currently
        # means no external dependancies.

        # Convert to Unicode
        query = args[0].decode('utf8')
        ## plpy.debug('1 query is %s' % repr(query))

        # Replace tsquery operators with ' '. '<' begins all the phrase
        # search operators, and a standalone '>' is fine.
        query = re.sub('[|&!<]', ' ', query)

        # Normalize whitespace
        query = re.sub("(?u)\s+"," ", query)

        # Convert AND, OR, NOT to tsearch2 punctuation
        query = re.sub(r"(?u)\bAND\b", "&", query)
        query = re.sub(r"(?u)\bOR\b", "|", query)
        query = re.sub(r"(?u)\bNOT\b", " !", query)
        ## plpy.debug('2 query is %s' % repr(query))

        # Deal with unwanted punctuation.
        # ':' is used in queries to specify a weight of a word.
        # '\' is treated differently in to_tsvector() and to_tsquery().
        punctuation = r'[:\\]'
        query = re.sub(r"(?u)%s+" % (punctuation,), " ", query)
        ## plpy.debug('3 query is %s' % repr(query))

        # Now that we have handle case sensitive booleans, convert to lowercase
        query = query.lower()

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

        return query or None
        $_$;


-- From 2209-53-1
CREATE OR REPLACE FUNCTION activity()
RETURNS SETOF pg_stat_activity
VOLATILE SECURITY DEFINER SET search_path = public
LANGUAGE plpgsql AS $$
DECLARE
    a pg_stat_activity%ROWTYPE;
BEGIN
    IF EXISTS (
            SELECT 1 FROM pg_attribute WHERE
                attrelid =
                    (SELECT oid FROM pg_class
                     WHERE relname = 'pg_stat_activity')
                AND attname = 'wait_event_type') THEN
        -- >= 9.6
        RETURN QUERY SELECT
            datid, datname, pid, usesysid, usename, application_name,
            client_addr, client_hostname, client_port, backend_start,
            xact_start, query_start, state_change, wait_event_type,
            wait_event, state, backend_xid, backend_xmin,
            CASE
                WHEN query LIKE '<IDLE>%'
                    OR query LIKE 'autovacuum:%'
                    THEN query
                ELSE
                    '<HIDDEN>'
            END AS query
        FROM pg_catalog.pg_stat_activity;
    ELSIF EXISTS (
            SELECT 1 FROM pg_attribute WHERE
                attrelid =
                    (SELECT oid FROM pg_class
                     WHERE relname = 'pg_stat_activity')
                AND attname = 'backend_xid') THEN
        -- >= 9.4
        RETURN QUERY SELECT
            datid, datname, pid, usesysid, usename, application_name,
            client_addr, client_hostname, client_port, backend_start,
            xact_start, query_start, state_change, waiting, state,
            backend_xid, backend_xmin,
            CASE
                WHEN query LIKE '<IDLE>%'
                    OR query LIKE 'autovacuum:%'
                    THEN query
                ELSE
                    '<HIDDEN>'
            END AS query
        FROM pg_catalog.pg_stat_activity;
    ELSE
        -- >= 9.2; anything older is unsupported
        RETURN QUERY SELECT
            datid, datname, pid, usesysid, usename, application_name,
            client_addr, client_hostname, client_port, backend_start,
            xact_start, query_start, state_change, waiting, state,
            CASE
                WHEN query LIKE '<IDLE>%'
                    OR query LIKE 'autovacuum:%'
                    THEN query
                ELSE
                    '<HIDDEN>'
            END AS query
        FROM pg_catalog.pg_stat_activity;
    END IF;
END;
$$;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 81, 0);

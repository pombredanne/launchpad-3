-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

CREATE OR REPLACE FUNCTION assert_patch_applied(
    major integer, minor integer, patch integer) RETURNS boolean
LANGUAGE plpythonu STABLE AS
$$
    rv = plpy.execute("""
        SELECT * FROM LaunchpadDatabaseRevision
        WHERE major=%d AND minor=%d AND patch=%d
        """ % (major, minor, patch))
    if len(rv) == 0:
        raise Exception(
            'patch-%d-%02d-%d not applied.' % (major, minor, patch))
    else:
        return True
$$;

COMMENT ON FUNCTION assert_patch_applied(integer, integer, integer) IS
'Raise an exception if the given database patch has not been applied.';


CREATE OR REPLACE FUNCTION sha1(text) RETURNS char(40)
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import hashlib
    return hashlib.sha1(args[0]).hexdigest()
$$;

COMMENT ON FUNCTION sha1(text) IS
    'Return the SHA1 one way cryptographic hash as a string of 40 hex digits';


CREATE OR REPLACE FUNCTION null_count(p_values anyarray) RETURNS integer
LANGUAGE plpgsql IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
DECLARE
    v_index integer;
    v_null_count integer := 0;
BEGIN
    FOR v_index IN array_lower(p_values,1)..array_upper(p_values,1) LOOP
        IF p_values[v_index] IS NULL THEN
            v_null_count := v_null_count + 1;
        END IF;
    END LOOP;
    RETURN v_null_count;
END;
$$;

COMMENT ON FUNCTION null_count(anyarray) IS
'Return the number of NULLs in the first row of the given array.';


CREATE OR REPLACE FUNCTION cursor_fetch(cur refcursor, n integer)
RETURNS SETOF record LANGUAGE plpgsql AS
$$
DECLARE
    r record;
    count integer;
BEGIN
    FOR count IN 1..n LOOP
        FETCH FORWARD FROM cur INTO r;
        IF NOT FOUND THEN
            RETURN;
        END IF;
        RETURN NEXT r;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION cursor_fetch(refcursor, integer) IS
'Fetch the next n items from a cursor. Work around for not being able to use FETCH inside a SELECT statement.';



CREATE OR REPLACE FUNCTION replication_lag() RETURNS interval
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO public AS
$$
    DECLARE
        v_lag interval;
    BEGIN
        SELECT INTO v_lag max(st_lag_time) FROM _sl.sl_status;
        RETURN v_lag;
    -- Slony-I not installed here - non-replicated setup.
    EXCEPTION
        WHEN invalid_schema_name THEN
            RETURN NULL;
        WHEN undefined_table THEN
            RETURN NULL;
    END;
$$;

COMMENT ON FUNCTION replication_lag() IS
'Returns the worst lag time in our cluster, or NULL if not a replicated installation. Only returns meaningful results on the lpmain replication set master.';


CREATE OR REPLACE FUNCTION replication_lag(node_id integer) RETURNS interval
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO public AS
$$
    DECLARE
        v_lag interval;
    BEGIN
        SELECT INTO v_lag st_lag_time FROM _sl.sl_status
            WHERE st_origin = _sl.getlocalnodeid('_sl')
                AND st_received = node_id;
        RETURN v_lag;
    -- Slony-I not installed here - non-replicated setup.
    EXCEPTION
        WHEN invalid_schema_name THEN
            RETURN NULL;
        WHEN undefined_table THEN
            RETURN NULL;
    END;
$$;

COMMENT ON FUNCTION replication_lag(integer) IS
'Returns the lag time of the lpmain replication set to the given node, or NULL if not a replicated installation. The node id parameter can be obtained by calling getlocalnodeid() on the relevant database. This function only returns meaningful results on the lpmain replication set master.';


CREATE OR REPLACE FUNCTION update_replication_lag_cache() RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
    BEGIN
        DELETE FROM DatabaseReplicationLag;
        INSERT INTO DatabaseReplicationLag (node, lag)
            SELECT st_received, st_lag_time FROM _sl.sl_status
            WHERE st_origin = _sl.getlocalnodeid('_sl');
        RETURN TRUE;
    -- Slony-I not installed here - non-replicated setup.
    EXCEPTION
        WHEN invalid_schema_name THEN
            RETURN FALSE;
        WHEN undefined_table THEN
            RETURN FALSE;
    END;
$$;

COMMENT ON FUNCTION update_replication_lag_cache() IS
'Updates the DatabaseReplicationLag materialized view.';

CREATE OR REPLACE FUNCTION update_database_stats() RETURNS void
LANGUAGE plpythonu VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
    import re
    import subprocess

    # Prune DatabaseTableStats and insert current data.
    # First, detect if the statistics have been reset.
    stats_reset = plpy.execute("""
        SELECT *
        FROM
            pg_catalog.pg_stat_user_tables AS NowStat,
            DatabaseTableStats AS LastStat
        WHERE
            LastStat.date_created = (
                SELECT max(date_created) FROM DatabaseTableStats)
            AND NowStat.schemaname = LastStat.schemaname
            AND NowStat.relname = LastStat.relname
            AND (
                NowStat.seq_scan < LastStat.seq_scan
                OR NowStat.idx_scan < LastStat.idx_scan
                OR NowStat.n_tup_ins < LastStat.n_tup_ins
                OR NowStat.n_tup_upd < LastStat.n_tup_upd
                OR NowStat.n_tup_del < LastStat.n_tup_del
                OR NowStat.n_tup_hot_upd < LastStat.n_tup_hot_upd)
        LIMIT 1
        """, 1).nrows() > 0
    if stats_reset:
        # The database stats have been reset. We cannot calculate
        # deltas because we do not know when this happened. So we trash
        # our records as they are now useless to us. We could be more
        # sophisticated about this, but this should only happen
        # when an admin explicitly resets the statistics or if the
        # database is rebuilt.
        plpy.notice("Stats wraparound. Purging DatabaseTableStats")
        plpy.execute("DELETE FROM DatabaseTableStats")
    else:
        plpy.execute("""
            DELETE FROM DatabaseTableStats
            WHERE date_created < (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                - CAST('21 days' AS interval));
            """)
    # Insert current data.
    plpy.execute("""
        INSERT INTO DatabaseTableStats
            SELECT
                CURRENT_TIMESTAMP AT TIME ZONE 'UTC',
                schemaname, relname, seq_scan, seq_tup_read,
                coalesce(idx_scan, 0), coalesce(idx_tup_fetch, 0),
                n_tup_ins, n_tup_upd, n_tup_del,
                n_tup_hot_upd, n_live_tup, n_dead_tup, last_vacuum,
                last_autovacuum, last_analyze, last_autoanalyze
            FROM pg_catalog.pg_stat_user_tables;
        """)

    # Prune DatabaseCpuStats. Calculate CPU utilization information
    # and insert current data.
    plpy.execute("""
        DELETE FROM DatabaseCpuStats
        WHERE date_created < (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            - CAST('21 days' AS interval));
        """)
    dbname = plpy.execute(
        "SELECT current_database() AS dbname", 1)[0]['dbname']
    ps = subprocess.Popen(
        ["ps", "-C", "postgres", "--no-headers", "-o", "cp,args"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    stdout, stderr = ps.communicate()
    cpus = {}
    # We make the username match non-greedy so the trailing \d eats
    # trailing digits from the database username. This collapses
    # lpnet1, lpnet2 etc. into just lpnet.
    ps_re = re.compile(
        r"(?m)^\s*(\d+)\spostgres:\s(\w+?)\d*\s%s\s" % dbname)
    for ps_match in ps_re.finditer(stdout):
        cpu, username = ps_match.groups()
        cpus[username] = int(cpu) + cpus.setdefault(username, 0)
    cpu_ins = plpy.prepare(
        "INSERT INTO DatabaseCpuStats (username, cpu) VALUES ($1, $2)",
        ["text", "integer"])
    for cpu_tuple in cpus.items():
        plpy.execute(cpu_ins, cpu_tuple)
$$;

COMMENT ON FUNCTION update_database_stats() IS
'Copies rows from pg_stat_user_tables into DatabaseTableStats. We use a stored procedure because it is problematic for us to grant permissions on objects in the pg_catalog schema.';

SET check_function_bodies=false; -- Handle forward references
CREATE OR REPLACE FUNCTION update_database_disk_utilization() RETURNS void
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
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
            pg_index
        WHERE
            pg_class_index.relkind = 'i'
            AND pg_table_is_visible(pg_class_table.oid)
            AND pg_class_index.relnamespace = pg_namespace_index.oid
            AND pg_class_table.relnamespace = pg_namespace_table.oid
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
            pg_class AS pg_class_toast
        WHERE
            pg_class_table.relnamespace = pg_namespace_table.oid
            AND pg_table_is_visible(pg_class_table.oid)
            AND pg_class_index.relnamespace = pg_namespace_index.oid
            AND pg_class_table.reltoastrelid = pg_class_toast.oid
            AND pg_class_index.oid = pg_class_toast.reltoastidxid
        ) AS whatever;
$$;
SET check_function_bodies=true; -- Handle forward references

CREATE OR REPLACE FUNCTION getlocalnodeid() RETURNS integer
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO public AS
$$
    DECLARE
        v_node_id integer;
    BEGIN
        SELECT INTO v_node_id _sl.getlocalnodeid('_sl');
        RETURN v_node_id;
    EXCEPTION
        WHEN invalid_schema_name THEN
            RETURN NULL;
    END;
$$;

COMMENT ON FUNCTION getlocalnodeid() IS
'Return the replication node id for this node, or NULL if not a replicated installation.';


CREATE OR REPLACE FUNCTION activity()
RETURNS SETOF pg_catalog.pg_stat_activity
LANGUAGE SQL VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
    SELECT
        datid, datname, procpid, usesysid, usename,
        CASE
            WHEN current_query LIKE '<IDLE>%'
                OR current_query LIKE 'autovacuum:%'
                THEN current_query
            ELSE
                '<HIDDEN>'
        END AS current_query,
        waiting, xact_start, query_start,
        backend_start, client_addr, client_port
    FROM pg_catalog.pg_stat_activity;
$$;

COMMENT ON FUNCTION activity() IS
'SECURITY DEFINER wrapper around pg_stat_activity allowing unprivileged users to access most of its information.';


/* This is created as a function so the same definition can be used with
    many tables
*/
CREATE OR REPLACE FUNCTION valid_name(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re
    name = args[0]
    pat = r"^[a-z0-9][a-z0-9\+\.\-]*\Z"
    if re.match(pat, name):
        return 1
    return 0
$$;

COMMENT ON FUNCTION valid_name(text)
    IS 'validate a name.

    Names must contain only lowercase letters, numbers, ., & -. They
    must start with an alphanumeric. They are ASCII only. Names are useful
    for mneumonic identifiers such as nicknames and as URL components.
    This specification is the same as the Debian product naming policy.

    Note that a valid name might be all integers, so there is a possible
    namespace conflict if URL traversal is possible by name as well as id.';


CREATE OR REPLACE FUNCTION valid_branch_name(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re
    name = args[0]
    pat = r"^(?i)[a-z0-9][a-z0-9+\.\-@_]*\Z"
    if re.match(pat, name):
        return 1
    return 0
$$;

COMMENT ON FUNCTION valid_branch_name(text)
    IS 'validate a branch name.

    As per valid_name, except we allow uppercase and @';


CREATE OR REPLACE FUNCTION valid_bug_name(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re
    name = args[0]
    pat = r"^[a-z][a-z0-9+\.\-]+$"
    if re.match(pat, name):
        return 1
    return 0
$$;

COMMENT ON FUNCTION valid_bug_name(text) IS 'validate a bug name

    As per valid_name, except numeric-only names are not allowed (including
    names that look like floats).';


CREATE OR REPLACE FUNCTION valid_debian_version(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re
    m = re.search("""^(?ix)
        ([0-9]+:)?
        ([0-9a-z][a-z0-9+:.~-]*?)
        (-[a-z0-9+.~]+)?
        $""", args[0])
    if m is None:
        return 0
    epoch, version, revision = m.groups()
    if not epoch:
        # Can''t contain : if no epoch
        if ":" in version:
            return 0
    if not revision:
        # Can''t contain - if no revision
        if "-" in version:
            return 0
    return 1
$$;

COMMENT ON FUNCTION valid_debian_version(text) IS 'validate a version number as per Debian Policy';


CREATE OR REPLACE FUNCTION sane_version(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re
    if re.search("""^(?ix)
        [0-9a-z]
        ( [0-9a-z] | [0-9a-z.-]*[0-9a-z] )*
        $""", args[0]):
        return 1
    return 0
$$;

COMMENT ON FUNCTION sane_version(text) IS 'A sane version number for use by ProductRelease and DistroRelease. We may make it less strict if required, but it would be nice if we can enforce simple version strings because we use them in URLs';


CREATE OR REPLACE FUNCTION valid_cve(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re
    name = args[0]
    pat = r"^(19|20)\d{2}-\d{4}$"
    if re.match(pat, name):
        return 1
    return 0
$$;

COMMENT ON FUNCTION valid_cve(text) IS 'validate a common vulnerability number as defined on www.cve.mitre.org, minus the CAN- or CVE- prefix.';


CREATE OR REPLACE FUNCTION valid_absolute_url(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    from urlparse import urlparse, uses_netloc
    # Extend list of schemes that specify netloc. We can drop sftp
    # with Python 2.5 in the DB.
    if 'git' not in uses_netloc:
        uses_netloc.insert(0, 'sftp')
        uses_netloc.insert(0, 'bzr')
        uses_netloc.insert(0, 'bzr+ssh')
        uses_netloc.insert(0, 'ssh') # Mercurial
        uses_netloc.insert(0, 'git')
    (scheme, netloc, path, params, query, fragment) = urlparse(args[0])
    return bool(scheme and netloc)
$$;

COMMENT ON FUNCTION valid_absolute_url(text) IS 'Ensure the given test is a valid absolute URL, containing both protocol and network location';


CREATE OR REPLACE FUNCTION valid_fingerprint(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re
    if re.match(r"[\dA-F]{40}", args[0]) is not None:
        return 1
    else:
        return 0
$$;

COMMENT ON FUNCTION valid_fingerprint(text) IS 'Returns true if passed a valid GPG fingerprint. Valid GPG fingerprints are a 40 character long hexadecimal number in uppercase.';


CREATE OR REPLACE FUNCTION valid_keyid(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re
    if re.match(r"[\dA-F]{8}", args[0]) is not None:
        return 1
    else:
        return 0
$$;

COMMENT ON FUNCTION valid_keyid(text) IS 'Returns true if passed a valid GPG keyid. Valid GPG keyids are an 8 character long hexadecimal number in uppercase (in reality, they are 16 characters long but we are using the ''common'' definition.';


CREATE OR REPLACE FUNCTION valid_regexp(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re
    try:
        re.compile(args[0])
    except:
        return False
    else:
        return True
$$;

COMMENT ON FUNCTION valid_regexp(text)
    IS 'Returns true if the input can be compiled as a regular expression.';


CREATE OR REPLACE FUNCTION you_are_your_own_member() RETURNS trigger
LANGUAGE plpgsql AS
$$
    BEGIN
        INSERT INTO TeamParticipation (person, team)
            VALUES (NEW.id, NEW.id);
        RETURN NULL;
    END;
$$;

COMMENT ON FUNCTION you_are_your_own_member() IS
    'Trigger function to ensure that every row added to the Person table gets a corresponding row in the TeamParticipation table, as per the TeamParticipationUsage page on the Launchpad wiki';

SET check_function_bodies=false; -- Handle forward references

CREATE OR REPLACE FUNCTION is_team(integer) returns boolean
LANGUAGE sql STABLE RETURNS NULL ON NULL INPUT AS
$$
    SELECT count(*)>0 FROM Person WHERE id=$1 AND teamowner IS NOT NULL;
$$;

COMMENT ON FUNCTION is_team(integer) IS
    'True if the given id identifies a team in the Person table';


CREATE OR REPLACE FUNCTION is_team(text) returns boolean
LANGUAGE sql STABLE RETURNS NULL ON NULL INPUT AS
$$
    SELECT count(*)>0 FROM Person WHERE name=$1 AND teamowner IS NOT NULL;
$$;

COMMENT ON FUNCTION is_team(text) IS
    'True if the given name identifies a team in the Person table';


CREATE OR REPLACE FUNCTION is_person(text) returns boolean
LANGUAGE sql STABLE RETURNS NULL ON NULL INPUT AS
$$
    SELECT count(*)>0 FROM Person WHERE name=$1 AND teamowner IS NULL;
$$;

COMMENT ON FUNCTION is_person(text) IS
    'True if the given name identifies a person in the Person table';

SET check_function_bodies=true;


CREATE OR REPLACE FUNCTION is_printable_ascii(text) RETURNS boolean
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    import re, string
    try:
        text = args[0].decode("ASCII")
    except UnicodeError:
        return False
    if re.search(r"^[%s]*$" % re.escape(string.printable), text) is None:
        return False
    return True
$$;

COMMENT ON FUNCTION is_printable_ascii(text) IS
    'True if the string is pure printable US-ASCII';


CREATE OR REPLACE FUNCTION mv_pillarname_distribution() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO PillarName (name, distribution)
        VALUES (NEW.name, NEW.id);
    ELSIF NEW.name != OLD.name THEN
        UPDATE PillarName SET name=NEW.name WHERE distribution=NEW.id;
    END IF;
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION mv_pillarname_distribution() IS
    'Trigger maintaining the PillarName table';


CREATE OR REPLACE FUNCTION mv_pillarname_product() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO PillarName (name, product, active)
        VALUES (NEW.name, NEW.id, NEW.active);
    ELSIF NEW.name != OLD.name OR NEW.active != OLD.active THEN
        UPDATE PillarName SET name=NEW.name, active=NEW.active
        WHERE product=NEW.id;
    END IF;
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION mv_pillarname_product() IS
    'Trigger maintaining the PillarName table';


CREATE OR REPLACE FUNCTION mv_pillarname_project() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO PillarName (name, project, active)
        VALUES (NEW.name, NEW.id, NEW.active);
    ELSIF NEW.name != OLD.name or NEW.active != OLD.active THEN
        UPDATE PillarName SET name=NEW.name, active=NEW.active
        WHERE project=NEW.id;
    END IF;
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION mv_pillarname_project() IS
    'Trigger maintaining the PillarName table';


CREATE OR REPLACE FUNCTION mv_pofiletranslator_translationmessage()
RETURNS TRIGGER VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
DECLARE
    v_trash_old BOOLEAN;
BEGIN
    -- If we are deleting a row, we need to remove the existing
    -- POFileTranslator row and reinsert the historical data if it exists.
    -- We also treat UPDATEs that change the key (submitter) the same
    -- as deletes. UPDATEs that don't change these columns are treated like
    -- INSERTs below.
    IF TG_OP = 'INSERT' THEN
        v_trash_old := FALSE;
    ELSIF TG_OP = 'DELETE' THEN
        v_trash_old := TRUE;
    ELSE -- UPDATE
        v_trash_old = (
            OLD.submitter != NEW.submitter
            );
    END IF;

    IF v_trash_old THEN
        -- Was this somebody's most-recently-changed message?
        -- If so, delete the entry for that change.
        DELETE FROM POFileTranslator
        WHERE latest_message = OLD.id;
        IF FOUND THEN
            -- We deleted the entry for somebody's latest contribution.
            -- Find that person's latest remaining contribution and
            -- create a new record for that.
            INSERT INTO POFileTranslator (
                person, pofile, latest_message, date_last_touched
                )
            SELECT DISTINCT ON (person, pofile.id)
                new_latest_message.submitter AS person,
                pofile.id,
                new_latest_message.id,
                greatest(new_latest_message.date_created,
                         new_latest_message.date_reviewed)
              FROM POFile
              JOIN TranslationTemplateItem AS old_template_item
                ON OLD.potmsgset = old_template_item.potmsgset AND
                   old_template_item.potemplate = pofile.potemplate AND
                   pofile.language = OLD.language
              JOIN TranslationTemplateItem AS new_template_item
                ON (old_template_item.potemplate =
                     new_template_item.potemplate)
              JOIN TranslationMessage AS new_latest_message
                ON new_latest_message.potmsgset =
                       new_template_item.potmsgset AND
                   new_latest_message.language = OLD.language
              LEFT OUTER JOIN POfileTranslator AS ExistingEntry
                ON ExistingEntry.person = OLD.submitter AND
                   ExistingEntry.pofile = POFile.id
              WHERE
                new_latest_message.submitter = OLD.submitter AND
                ExistingEntry IS NULL
              ORDER BY new_latest_message.submitter, pofile.id,
                       new_latest_message.date_created DESC,
                       new_latest_message.id DESC;
        END IF;

        -- No NEW with DELETE, so we can short circuit and leave.
        IF TG_OP = 'DELETE' THEN
            RETURN NULL; -- Ignored because this is an AFTER trigger
        END IF;
    END IF;

    -- Standard 'upsert' loop to avoid race conditions.
    LOOP
        UPDATE POFileTranslator
        SET
            date_last_touched = CURRENT_TIMESTAMP AT TIME ZONE 'UTC',
            latest_message = NEW.id
        FROM POFile, TranslationTemplateItem
        WHERE person = NEW.submitter AND
              TranslationTemplateItem.potmsgset=NEW.potmsgset AND
              TranslationTemplateItem.potemplate=pofile.potemplate AND
              pofile.language=NEW.language AND
              POFileTranslator.pofile = pofile.id;
        IF found THEN
            RETURN NULL; -- Return value ignored as this is an AFTER trigger
        END IF;

        BEGIN
            INSERT INTO POFileTranslator (person, pofile, latest_message)
            SELECT DISTINCT ON (NEW.submitter, pofile.id)
                NEW.submitter, pofile.id, NEW.id
              FROM TranslationTemplateItem
              JOIN POFile
                ON pofile.language = NEW.language AND
                   pofile.potemplate = translationtemplateitem.potemplate
              WHERE
                TranslationTemplateItem.potmsgset = NEW.potmsgset;
            RETURN NULL; -- Return value ignored as this is an AFTER trigger
        EXCEPTION WHEN unique_violation THEN
            -- do nothing
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mv_pofiletranslator_translationmessage() IS
    'Trigger maintaining the POFileTranslator table';

CREATE OR REPLACE FUNCTION person_sort_key(displayname text, name text)
RETURNS text
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    # NB: If this implementation is changed, the person_sort_idx needs to be
    # rebuilt along with any other indexes using it.
    import re

    try:
        strip_re = SD["strip_re"]
    except KeyError:
        strip_re = re.compile("(?:[^\w\s]|[\d_])", re.U)
        SD["strip_re"] = strip_re

    displayname, name = args

    # Strip noise out of displayname. We do not have to bother with
    # name, as we know it is just plain ascii.
    displayname = strip_re.sub('', displayname.decode('UTF-8').lower())
    return ("%s, %s" % (displayname.strip(), name)).encode('UTF-8')
$$;

COMMENT ON FUNCTION person_sort_key(text,text) IS 'Return a string suitable for sorting people on, generated by stripping noise out of displayname and concatenating name';


CREATE OR REPLACE FUNCTION debversion_sort_key(version text) RETURNS text
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    # If this method is altered, then any functional indexes using it
    # need to be rebuilt.
    import re

    VERRE = re.compile("(?:([0-9]+):)?(.+?)(?:-([^-]+))?$")

    MAP = "0123456789ABCDEFGHIJKLMNOPQRSTUV"

    epoch, version, release = VERRE.match(args[0]).groups()
    key = []
    for part, part_weight in ((epoch, 3000), (version, 2000), (release, 1000)):
        if not part:
            continue
        i = 0
        l = len(part)
        while i != l:
            c = part[i]
            if c.isdigit():
                key.append(part_weight)
                j = i
                while i != l and part[i].isdigit(): i += 1
                key.append(part_weight+int(part[j:i] or "0"))
            elif c == "~":
                key.append(0)
                i += 1
            elif c.isalpha():
                key.append(part_weight+ord(c))
                i += 1
            else:
                key.append(part_weight+256+ord(c))
                i += 1
        if not key or key[-1] != part_weight:
            key.append(part_weight)
            key.append(part_weight)
    key.append(1)

    # Encode our key and return it
    #
    result = []
    for value in key:
        if not value:
            result.append("000")
        else:
            element = []
            while value:
                element.insert(0, MAP[value & 0x1F])
                value >>= 5
            element_len = len(element)
            if element_len < 3:
                element.insert(0, "0"*(3-element_len))
            elif element_len == 3:
                pass
            elif element_len < 35:
                element.insert(0, MAP[element_len-4])
                element.insert(0, "X")
            elif element_len < 1027:
                element.insert(0, MAP[(element_len-4) & 0x1F])
                element.insert(0, MAP[(element_len-4) & 0x3E0])
                element.insert(0, "Y")
            else:
                raise ValueError("Number too large")
            result.extend(element)
    return "".join(result)
$$;

COMMENT ON FUNCTION debversion_sort_key(text) IS 'Return a string suitable for sorting debian version strings on';


CREATE OR REPLACE FUNCTION name_blacklist_match(text, integer) RETURNS int4
LANGUAGE plpythonu STABLE RETURNS NULL ON NULL INPUT
SECURITY DEFINER SET search_path TO public AS
$$
    import re
    name = args[0].decode("UTF-8")
    user_id = args[1]

    # Initialize shared storage, shared between invocations.
    if not SD.has_key("regexp_select_plan"):

        # All the blacklist regexps except the ones we are an admin
        # for. These we do not check since they are not blacklisted to us.
        SD["regexp_select_plan"] = plpy.prepare("""
            SELECT id, regexp FROM NameBlacklist
            WHERE admin IS NULL OR admin NOT IN (
                SELECT team FROM TeamParticipation
                WHERE person = $1)
            ORDER BY id
            """, ["integer"])

        # Storage for compiled regexps
        SD["compiled"] = {}

        # admins is a celebrity and its id is immutable.
        admins_id = plpy.execute(
            "SELECT id FROM Person WHERE name='admins'")[0]["id"]

        SD["admin_select_plan"] = plpy.prepare("""
            SELECT TRUE FROM TeamParticipation
            WHERE
                TeamParticipation.team = %d
                AND TeamParticipation.person = $1
            LIMIT 1
            """ % admins_id, ["integer"])

        # All the blacklist regexps except those that have an admin because
        # members of ~admin can use any name that any other admin can use.
        SD["admin_regexp_select_plan"] = plpy.prepare("""
            SELECT id, regexp FROM NameBlacklist
            WHERE admin IS NULL
            ORDER BY id
            """, ["integer"])


    compiled = SD["compiled"]

    # Names are never blacklisted for Lauchpad admins.
    if user_id is not None and plpy.execute(
        SD["admin_select_plan"], [user_id]).nrows() > 0:
        blacklist_plan = "admin_regexp_select_plan"
    else:
        blacklist_plan = "regexp_select_plan"

    for row in plpy.execute(SD[blacklist_plan], [user_id]):
        regexp_id = row["id"]
        regexp_txt = row["regexp"]
        if (compiled.get(regexp_id) is None
            or compiled[regexp_id][0] != regexp_txt):
            regexp = re.compile(
                regexp_txt, re.IGNORECASE | re.UNICODE | re.VERBOSE
                )
            compiled[regexp_id] = (regexp_txt, regexp)
        else:
            regexp = compiled[regexp_id][1]
        if regexp.search(name) is not None:
            return regexp_id
    return None
$$;

COMMENT ON FUNCTION name_blacklist_match(text, integer) IS 'Return the id of the row in the NameBlacklist table that matches the given name, or NULL if no regexps in the NameBlacklist table match.';


CREATE OR REPLACE FUNCTION is_blacklisted_name(text, integer)
RETURNS boolean LANGUAGE SQL STABLE RETURNS NULL ON NULL INPUT
SECURITY DEFINER SET search_path TO public AS
$$
    SELECT COALESCE(name_blacklist_match($1, $2)::boolean, FALSE);
$$;

COMMENT ON FUNCTION is_blacklisted_name(text, integer) IS 'Return TRUE if any regular expressions stored in the NameBlacklist table match the givenname, otherwise return FALSE.';


CREATE OR REPLACE FUNCTION set_shipit_normalized_address() RETURNS trigger
LANGUAGE plpgsql AS
$$
    BEGIN
        NEW.normalized_address =
            lower(
                -- Strip off everything that's not alphanumeric
                -- characters.
                regexp_replace(
                    coalesce(NEW.addressline1, '') || ' ' ||
                    coalesce(NEW.addressline2, '') || ' ' ||
                    coalesce(NEW.city, ''),
                    '[^a-zA-Z0-9]+', '', 'g'));
        RETURN NEW;
    END;
$$;

COMMENT ON FUNCTION set_shipit_normalized_address() IS 'Store a normalized concatenation of the request''s address into the normalized_address column.';

CREATE OR REPLACE FUNCTION generate_openid_identifier() RETURNS text
LANGUAGE plpythonu VOLATILE AS
$$
    from random import choice

    # Non display confusing characters.
    chars = '34678bcdefhkmnprstwxyzABCDEFGHJKLMNPQRTWXY'

    # Character length of tokens. Can be increased, decreased or even made
    # random - Launchpad does not care. 7 means it takes 40 bytes to store
    # a null-terminated Launchpad identity URL on the current domain name.
    length=7

    loop_count = 0
    while loop_count < 20000:
        # Generate a random openid_identifier
        oid = ''.join(choice(chars) for count in range(length))

        # Check if the oid is already in the db, although this is pretty
        # unlikely
        rv = plpy.execute("""
            SELECT COUNT(*) AS num FROM Account WHERE openid_identifier = '%s'
            """ % oid, 1)
        if rv[0]['num'] == 0:
            return oid
        loop_count += 1
        if loop_count == 1:
            plpy.warning(
                'Clash generating unique openid_identifier. '
                'Increase length if you see this warning too much.')
    plpy.error(
        "Unable to generate unique openid_identifier. "
        "Need to increase length of tokens.")
$$;


--
-- Obsolete - remove after next baseline
--
CREATE OR REPLACE FUNCTION set_openid_identifier() RETURNS trigger
LANGUAGE plpythonu AS
$$
    # If someone is trying to explicitly set the openid_identifier, let them.
    # This also causes openid_identifiers to be left alone if this is an
    # UPDATE trigger.
    if TD['new']['openid_identifier'] is not None:
        return None

    from random import choice

    # Non display confusing characters
    chars = '34678bcdefhkmnprstwxyzABCDEFGHJKLMNPQRTWXY'

    # character length of tokens. Can be increased, decreased or even made
    # random - Launchpad does not care. 7 means it takes 40 bytes to store
    # a null-terminated Launchpad identity URL on the current domain name.
    length=7

    loop_count = 0
    while loop_count < 20000:
        # Generate a random openid_identifier
        oid = ''.join(choice(chars) for count in range(length))

        # Check if the oid is already in the db, although this is pretty
        # unlikely
        rv = plpy.execute("""
            SELECT COUNT(*) AS num FROM Person WHERE openid_identifier = '%s'
            """ % oid, 1)
        if rv[0]['num'] == 0:
            TD['new']['openid_identifier'] = oid
            return "MODIFY"
        loop_count += 1
        if loop_count == 1:
            plpy.warning(
                'Clash generating unique openid_identifier. '
                'Increase length if you see this warning too much.')
    plpy.error(
        "Unable to generate unique openid_identifier. "
        "Need to increase length of tokens.")
$$;


CREATE OR REPLACE FUNCTION set_bug_date_last_message() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE Bug
        SET date_last_message = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        WHERE Bug.id = NEW.bug;
    ELSE
        UPDATE Bug
        SET date_last_message = max_datecreated
        FROM (
            SELECT BugMessage.bug, max(Message.datecreated) AS max_datecreated
            FROM BugMessage, Message
            WHERE BugMessage.id <> OLD.id
                AND BugMessage.bug = OLD.bug
                AND BugMessage.message = Message.id
            GROUP BY BugMessage.bug
            ) AS MessageSummary
        WHERE Bug.id = MessageSummary.bug;
    END IF;
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION set_bug_date_last_message() IS 'AFTER INSERT trigger on BugMessage maintaining the Bug.date_last_message column';


CREATE OR REPLACE FUNCTION set_bug_number_of_duplicates() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE AS
$$
BEGIN
    -- Short circuit on an update that doesn't change duplicateof
    IF TG_OP = 'UPDATE' THEN
        IF NEW.duplicateof = OLD.duplicateof THEN
            RETURN NULL; -- Ignored - this is an AFTER trigger
        END IF;
    END IF;

    -- For update or delete, possibly decrement a bug's dupe count
    IF TG_OP <> 'INSERT' THEN
        IF OLD.duplicateof IS NOT NULL THEN
            UPDATE Bug SET number_of_duplicates = number_of_duplicates - 1
                WHERE Bug.id = OLD.duplicateof;
        END IF;
    END IF;

    -- For update or insert, possibly increment a bug's dupe cout
    IF TG_OP <> 'DELETE' THEN
        IF NEW.duplicateof IS NOT NULL THEN
            UPDATE Bug SET number_of_duplicates = number_of_duplicates + 1
                WHERE Bug.id = NEW.duplicateof;
        END IF;
    END IF;

    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION set_bug_number_of_duplicates() IS
'AFTER UPDATE trigger on Bug maintaining the Bug.number_of_duplicates column';

CREATE OR REPLACE FUNCTION set_bug_message_count() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.bug = OLD.bug THEN
            RETURN NULL; -- Ignored - this is an AFTER trigger.
        END IF;
    END IF;

    IF TG_OP <> 'DELETE' THEN
        UPDATE Bug SET message_count = message_count + 1
        WHERE Bug.id = NEW.bug;
    END IF;

    IF TG_OP <> 'INSERT' THEN
        UPDATE Bug SET message_count = message_count - 1
        WHERE Bug.id = OLD.bug;
    END IF;

    RETURN NULL; -- Ignored - this is an AFTER trigger.
END;
$$;

COMMENT ON FUNCTION set_bug_message_count() IS
'AFTER UPDATE trigger on BugMessage maintaining the Bug.message_count column';


CREATE OR REPLACE FUNCTION set_date_status_set() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    IF OLD.status <> NEW.status THEN
        NEW.date_status_set = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION set_date_status_set() IS 'BEFORE UPDATE trigger on Account that maintains the Account.date_status_set column.';


CREATE OR REPLACE FUNCTION ulower(text) RETURNS text
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    return args[0].decode('utf8').lower().encode('utf8')
$$;

COMMENT ON FUNCTION ulower(text) IS
'Return the lower case version of a UTF-8 encoded string.';


CREATE OR REPLACE FUNCTION set_bug_users_affected_count() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.affected = TRUE THEN
            UPDATE Bug
            SET users_affected_count = users_affected_count + 1
            WHERE Bug.id = NEW.bug;
        ELSE
            UPDATE Bug
            SET users_unaffected_count = users_unaffected_count + 1
            WHERE Bug.id = NEW.bug;
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        IF OLD.affected = TRUE THEN
            UPDATE Bug
            SET users_affected_count = users_affected_count - 1
            WHERE Bug.id = OLD.bug;
        ELSE
            UPDATE Bug
            SET users_unaffected_count = users_unaffected_count - 1
            WHERE Bug.id = OLD.bug;
        END IF;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF OLD.affected <> NEW.affected THEN
            IF NEW.affected THEN
                UPDATE Bug
                SET users_affected_count = users_affected_count + 1,
                    users_unaffected_count = users_unaffected_count - 1
                WHERE Bug.id = OLD.bug;
            ELSE
                UPDATE Bug
                SET users_affected_count = users_affected_count - 1,
                    users_unaffected_count = users_unaffected_count + 1
                WHERE Bug.id = OLD.bug;
            END IF;
        END IF;
    END IF;

    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION set_bug_message_count() IS
'AFTER UPDATE trigger on BugAffectsPerson maintaining the Bug.users_affected_count column';


CREATE OR REPLACE FUNCTION set_bugtask_date_milestone_set() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- If the inserted row as a milestone set, set date_milestone_set.
        IF NEW.milestone IS NOT NULL THEN
            UPDATE BugTask
            SET date_milestone_set = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            WHERE BugTask.id = NEW.id;
        END IF;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF OLD.milestone IS NULL THEN
            -- If there was no milestone set, check if the new row has a
            -- milestone set and set date_milestone_set.
            IF NEW.milestone IS NOT NULL THEN
                UPDATE BugTask
                SET date_milestone_set = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                WHERE BugTask.id = NEW.id;
            END IF;
        ELSE
            IF NEW.milestone IS NULL THEN
                -- If the milestone was unset, clear date_milestone_set.
                UPDATE BugTask
                SET date_milestone_set = NULL
                WHERE BugTask.id = NEW.id;
            ELSE
                -- Update date_milestone_set if the bug task was
                -- targeted to another milestone.
                IF NEW.milestone != OLD.milestone THEN
                    UPDATE BugTask
                    SET date_milestone_set = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                    WHERE BugTask.id = NEW.id;
                END IF;

            END IF;
        END IF;
    END IF;

    RETURN NULL; -- Ignored - this is an AFTER trigger.
END;
$$;

COMMENT ON FUNCTION set_bugtask_date_milestone_set() IS
'Update BugTask.date_milestone_set when BugTask.milestone is changed.';

CREATE OR REPLACE FUNCTION packageset_inserted_trig() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    -- A new package set was inserted; make it a descendent of itself in
    -- the flattened package set inclusion table in order to facilitate
    -- querying.
    INSERT INTO flatpackagesetinclusion(parent, child)
      VALUES (NEW.id, NEW.id);
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION packageset_inserted_trig() IS
'Insert self-referencing DAG edge when a new package set is inserted.';

CREATE OR REPLACE FUNCTION packageset_deleted_trig() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    DELETE FROM flatpackagesetinclusion
      WHERE parent = OLD.id AND child = OLD.id;

    -- A package set was deleted; it may have participated in package set
    -- inclusion relations in a sub/superset role; delete all inclusion
    -- relationships in which it participated.
    DELETE FROM packagesetinclusion
      WHERE parent = OLD.id OR child = OLD.id;
    RETURN OLD;
END;
$$;

COMMENT ON FUNCTION packageset_deleted_trig() IS
'Remove any DAG edges leading to/from the deleted package set.';

CREATE OR REPLACE FUNCTION packagesetinclusion_inserted_trig() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    DECLARE
        parent_name text;
        child_name text;
        parent_distroseries text;
        child_distroseries text;
    BEGIN
        -- Make sure that the package sets being associated here belong
        -- to the same distro series.
        IF (SELECT parent.distroseries != child.distroseries
            FROM packageset parent, packageset child
            WHERE parent.id = NEW.parent AND child.id = NEW.child)
        THEN
            SELECT name INTO parent_name FROM packageset WHERE id = NEW.parent;
            SELECT name INTO child_name FROM packageset WHERE id = NEW.child;
            SELECT ds.name INTO parent_distroseries FROM packageset ps, distroseries ds WHERE ps.id = NEW.parent AND ps.distroseries = ds.id;
            SELECT ds.name INTO child_distroseries FROM packageset ps, distroseries ds WHERE ps.id = NEW.child AND ps.distroseries = ds.id;
            RAISE EXCEPTION 'Package sets % and % belong to different distro series (to % and % respectively) and thus cannot be associated.', child_name, parent_name, child_distroseries, parent_distroseries;
        END IF;

        IF EXISTS(
            SELECT * FROM flatpackagesetinclusion
            WHERE parent = NEW.child AND child = NEW.parent LIMIT 1)
        THEN
            SELECT name INTO parent_name FROM packageset WHERE id = NEW.parent;
            SELECT name INTO child_name FROM packageset WHERE id = NEW.child;
            RAISE EXCEPTION 'Package set % already includes %. Adding (% -> %) would introduce a cycle in the package set graph (DAG).', child_name, parent_name, parent_name, child_name;
        END IF;
    END;
    -- A new package set inclusion relationship was inserted i.e. a set M
    -- now includes another set N as a subset.
    -- For an explanation of the queries below please see page 4 of
    -- "Maintaining Transitive Closure of Graphs in SQL"
    -- http://www.comp.nus.edu.sg/~wongls/psZ/dlsw-ijit97-16.ps
    CREATE TEMP TABLE tmp_fpsi_new(
        parent integer NOT NULL,
        child integer NOT NULL);

    INSERT INTO tmp_fpsi_new (
        SELECT
            X.parent AS parent, NEW.child AS child
        FROM flatpackagesetinclusion X WHERE X.child = NEW.parent
      UNION
        SELECT
            NEW.parent AS parent, X.child AS child
        FROM flatpackagesetinclusion X WHERE X.parent = NEW.child
      UNION
        SELECT
            X.parent AS parent, Y.child AS child
        FROM flatpackagesetinclusion X, flatpackagesetinclusion Y
        WHERE X.child = NEW.parent AND Y.parent = NEW.child
        );
    INSERT INTO tmp_fpsi_new(parent, child) VALUES(NEW.parent, NEW.child);

    INSERT INTO flatpackagesetinclusion(parent, child) (
        SELECT
            parent, child FROM tmp_fpsi_new
        EXCEPT
        SELECT F.parent, F.child FROM flatpackagesetinclusion F
        );

    DROP TABLE tmp_fpsi_new;

    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION packagesetinclusion_inserted_trig() IS
'Maintain the transitive closure in the DAG for a newly inserted edge leading to/from a package set.';

CREATE OR REPLACE FUNCTION packagesetinclusion_deleted_trig() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    -- A package set inclusion relationship was deleted i.e. a set M
    -- ceases to include another set N as a subset.
    -- For an explanation of the queries below please see page 5 of
    -- "Maintaining Transitive Closure of Graphs in SQL"
    -- http://www.comp.nus.edu.sg/~wongls/psZ/dlsw-ijit97-16.ps
    CREATE TEMP TABLE tmp_fpsi_suspect(
        parent integer NOT NULL,
        child integer NOT NULL);
    CREATE TEMP TABLE tmp_fpsi_trusted(
        parent integer NOT NULL,
        child integer NOT NULL);
    CREATE TEMP TABLE tmp_fpsi_good(
        parent integer NOT NULL,
        child integer NOT NULL);

    INSERT INTO tmp_fpsi_suspect (
        SELECT X.parent, Y.child
        FROM flatpackagesetinclusion X, flatpackagesetinclusion Y
        WHERE X.child = OLD.parent AND Y.parent = OLD.child
      UNION
        SELECT X.parent, OLD.child FROM flatpackagesetinclusion X
        WHERE X.child = OLD.parent
      UNION
        SELECT OLD.parent, X.child FROM flatpackagesetinclusion X
        WHERE X.parent = OLD.child
      UNION
        SELECT OLD.parent, OLD.child
        );

    INSERT INTO tmp_fpsi_trusted (
        SELECT parent, child FROM flatpackagesetinclusion
        EXCEPT
        SELECT parent, child FROM tmp_fpsi_suspect
      UNION
        SELECT parent, child FROM packagesetinclusion psi
        WHERE psi.parent != OLD.parent AND psi.child != OLD.child
        );

    INSERT INTO tmp_fpsi_good (
        SELECT parent, child FROM tmp_fpsi_trusted
      UNION
        SELECT T1.parent, T2.child
        FROM tmp_fpsi_trusted T1, tmp_fpsi_trusted T2
        WHERE T1.child = T2.parent
      UNION
        SELECT T1.parent, T3.child
        FROM tmp_fpsi_trusted T1, tmp_fpsi_trusted T2, tmp_fpsi_trusted T3
        WHERE T1.child = T2.parent AND T2.child = T3.parent
        );

    DELETE FROM flatpackagesetinclusion fpsi
    WHERE NOT EXISTS (
        SELECT * FROM tmp_fpsi_good T
        WHERE T.parent = fpsi.parent AND T.child = fpsi.child);

    DROP TABLE tmp_fpsi_good;
    DROP TABLE tmp_fpsi_trusted;
    DROP TABLE tmp_fpsi_suspect;

    RETURN OLD;
END;
$$;

COMMENT ON FUNCTION packagesetinclusion_deleted_trig() IS
'Maintain the transitive closure in the DAG when an edge leading to/from a package set is deleted.';


CREATE OR REPLACE FUNCTION update_branch_name_cache() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
DECLARE
    needs_update boolean := FALSE;
BEGIN
    IF TG_OP = 'INSERT' THEN
        needs_update := TRUE;
    ELSIF (NEW.owner_name IS NULL
        OR NEW.unique_name IS NULL
        OR OLD.owner_name <> NEW.owner_name
        OR OLD.unique_name <> NEW.unique_name
        OR (NEW.target_suffix IS NULL <> OLD.target_suffix IS NULL)
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

COMMENT ON FUNCTION update_branch_name_cache() IS
'Maintain the cached name columns in Branch.';


CREATE OR REPLACE FUNCTION mv_branch_person_update() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
DECLARE
    v_branch RECORD;
BEGIN
    IF OLD.id != NEW.id THEN
        RAISE EXCEPTION 'Cannot change Person.id';
    END IF;
    IF OLD.name != NEW.name THEN
        UPDATE Branch SET owner_name = NEW.name WHERE owner = NEW.id;
    END IF;
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION mv_branch_person_update() IS
'Maintain Branch name cache when Person is modified.';


CREATE OR REPLACE FUNCTION mv_branch_product_update() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
DECLARE
    v_branch RECORD;
BEGIN
    IF OLD.id != NEW.id THEN
        RAISE EXCEPTION 'Cannot change Product.id';
    END IF;
    IF OLD.name != NEW.name THEN
        UPDATE Branch SET target_suffix = NEW.name WHERE product=NEW.id;
    END IF;
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION mv_branch_product_update() IS
'Maintain Branch name cache when Product is modified.';


CREATE OR REPLACE FUNCTION mv_branch_distroseries_update() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    IF OLD.id != NEW.id THEN
        RAISE EXCEPTION 'Cannot change Distroseries.id';
    END IF;
    IF OLD.name != NEW.name THEN
        UPDATE Branch SET unique_name = NULL
        WHERE Branch.distroseries = NEW.id;
    END IF;
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION mv_branch_distroseries_update() IS
'Maintain Branch name cache when Distroseries is modified.';


CREATE OR REPLACE FUNCTION mv_branch_distribution_update() RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    IF OLD.id != NEW.id THEN
        RAISE EXCEPTION 'Cannot change Distribution.id';
    END IF;
    IF OLD.name != NEW.name THEN
        UPDATE Branch SET unique_name = NULL
        FROM DistroSeries
        WHERE Branch.distroseries = Distroseries.id
            AND Distroseries.distribution = NEW.id;
    END IF;
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION mv_branch_distribution_update() IS
'Maintain Branch name cache when Distribution is modified.';


-- Mirror tables for the login service.
-- We maintain a duplicate of a few tables which are replicated
-- in a seperate replication set.
-- Insert triggers
CREATE OR REPLACE FUNCTION lp_mirror_teamparticipation_ins() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    INSERT INTO lp_TeamParticipation SELECT NEW.*;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE OR REPLACE FUNCTION lp_mirror_personlocation_ins() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    INSERT INTO lp_PersonLocation SELECT NEW.*;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE OR REPLACE FUNCTION lp_mirror_person_ins() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    INSERT INTO lp_Person (
        id, displayname, teamowner, teamdescription, name, language, fti,
        defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy,
        merged, datecreated, homepage_content, icon, mugshot,
        hide_email_addresses, creation_rationale, creation_comment,
        registrant, logo, renewal_policy, personal_standing,
        personal_standing_reason, mail_resumption_date,
        mailing_list_auto_subscribe_policy, mailing_list_receive_duplicates,
        visibility, verbose_bugnotifications, account)
        SELECT NEW.*;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

-- Obsolete. Remove next cycle.
CREATE OR REPLACE FUNCTION lp_mirror_account_ins() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    INSERT INTO lp_Account (id, openid_identifier)
    VALUES (NEW.id, NEW.openid_identifier);
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE OR REPLACE FUNCTION lp_mirror_openididentifier_ins() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    -- Support obsolete lp_Account.openid_identifier as best we can
    -- until ISD migrates to using lp_OpenIdIdentifier.
    UPDATE lp_account SET openid_identifier = NEW.identifier
    WHERE id = NEW.account;
    IF NOT found THEN
        INSERT INTO lp_account (id, openid_identifier)
        VALUES (NEW.account, NEW.identifier);
    END IF;

    INSERT INTO lp_OpenIdIdentifier (identifier, account, date_created)
    VALUES (NEW.identifier, NEW.account, NEW.date_created);

    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

-- UPDATE triggers
CREATE  OR REPLACE FUNCTION lp_mirror_teamparticipation_upd() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    UPDATE lp_TeamParticipation
    SET id = NEW.id,
        team = NEW.team,
        person = NEW.person
    WHERE id = OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE  OR REPLACE FUNCTION lp_mirror_personlocation_upd() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    UPDATE lp_PersonLocation
    SET id = NEW.id,
        date_created = NEW.date_created,
        person = NEW.person,
        latitude = NEW.latitude,
        longitude = NEW.longitude,
        time_zone = NEW.time_zone,
        last_modified_by = NEW.last_modified_by,
        date_last_modified = NEW.date_last_modified,
        visible = NEW.visible,
        locked = NEW.locked
    WHERE id = OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE  OR REPLACE FUNCTION lp_mirror_person_upd() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    UPDATE lp_Person
    SET id = NEW.id,
        displayname = NEW.displayname,
        teamowner = NEW.teamowner,
        teamdescription = NEW.teamdescription,
        name = NEW.name,
        language = NEW.language,
        fti = NEW.fti,
        defaultmembershipperiod = NEW.defaultmembershipperiod,
        defaultrenewalperiod = NEW.defaultrenewalperiod,
        subscriptionpolicy = NEW.subscriptionpolicy,
        merged = NEW.merged,
        datecreated = NEW.datecreated,
        homepage_content = NEW.homepage_content,
        icon = NEW.icon,
        mugshot = NEW.mugshot,
        hide_email_addresses = NEW.hide_email_addresses,
        creation_rationale = NEW.creation_rationale,
        creation_comment = NEW.creation_comment,
        registrant = NEW.registrant,
        logo = NEW.logo,
        renewal_policy = NEW.renewal_policy,
        personal_standing = NEW.personal_standing,
        personal_standing_reason = NEW.personal_standing_reason,
        mail_resumption_date = NEW.mail_resumption_date,
        mailing_list_auto_subscribe_policy
            = NEW.mailing_list_auto_subscribe_policy,
        mailing_list_receive_duplicates = NEW.mailing_list_receive_duplicates,
        visibility = NEW.visibility,
        verbose_bugnotifications = NEW.verbose_bugnotifications,
        account = NEW.account
    WHERE id = OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE OR REPLACE FUNCTION lp_mirror_account_upd() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF OLD.id <> NEW.id OR OLD.openid_identifier <> NEW.openid_identifier THEN
        UPDATE lp_Account
        SET id = NEW.id, openid_identifier = NEW.openid_identifier
        WHERE id = OLD.id;
    END IF;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE OR REPLACE FUNCTION lp_mirror_openididentifier_upd() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF OLD.identifier <> NEW.identifier THEN
        UPDATE lp_Account SET openid_identifier = NEW.identifier
        WHERE openid_identifier = OLD.identifier;
    END IF;
    UPDATE lp_OpenIdIdentifier
    SET
        identifier = NEW.identifier,
        account = NEW.account,
        date_created = NEW.date_created
    WHERE identifier = OLD.identifier;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

-- Delete triggers
CREATE OR REPLACE FUNCTION lp_mirror_del() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    EXECUTE 'DELETE FROM lp_' || TG_TABLE_NAME || ' WHERE id=' || OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE OR REPLACE FUNCTION lp_mirror_openididentifier_del() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
DECLARE
    next_identifier text;
BEGIN
    SELECT INTO next_identifier identifier FROM OpenIdIdentifier
    WHERE account = OLD.account AND identifier <> OLD.identifier
    ORDER BY date_created DESC LIMIT 1;

    IF next_identifier IS NOT NULL THEN
        UPDATE lp_account SET openid_identifier = next_identifier
        WHERE openid_identifier = OLD.identifier;
    ELSE
        DELETE FROM lp_account WHERE openid_identifier = OLD.identifier;
    END IF;

    DELETE FROM lp_OpenIdIdentifier WHERE identifier = OLD.identifier;

    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE OR REPLACE FUNCTION add_test_openid_identifier(account_ integer)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    -- The generated OpenIdIdentifier is not a valid OpenId Identity URL
    -- and does not match tokens generated by the Canonical SSO. They
    -- are only useful to the test suite, and access to this stored
    -- procedure on production does not allow you to compromise
    -- accounts.
    INSERT INTO OpenIdIdentifier (identifier, account)
    VALUES ('test' || CAST(account_ AS text), account_);
    RETURN TRUE;
EXCEPTION
    WHEN unique_violation THEN
        RETURN FALSE;
END;
$$;

COMMENT ON FUNCTION add_test_openid_identifier(integer) IS
'Add an OpenIdIdentifier to an account that can be used to login in the test environment. These identifiers are not usable on production or staging.';

-- Update the (redundant) column bug.latest_patch_uploaded when a
-- a bug attachment is added or removed or if its type is changed.
CREATE OR REPLACE FUNCTION bug_update_latest_patch_uploaded(integer)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    UPDATE bug SET latest_patch_uploaded =
        (SELECT max(message.datecreated)
            FROM message, bugattachment
            WHERE bugattachment.message=message.id AND
                bugattachment.bug=$1 AND
                bugattachment.type=1)
        WHERE bug.id=$1;
END;
$$;


CREATE OR REPLACE FUNCTION bug_update_latest_patch_uploaded_on_insert_update()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    PERFORM bug_update_latest_patch_uploaded(NEW.bug);
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;


CREATE OR REPLACE FUNCTION bug_update_latest_patch_uploaded_on_delete()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    PERFORM bug_update_latest_patch_uploaded(OLD.bug);
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;


CREATE OR REPLACE FUNCTION calculate_bug_heat(bug_id integer) RETURNS integer
LANGUAGE plpythonu STABLE RETURNS NULL ON NULL INPUT AS $$
    from datetime import datetime

    class BugHeatConstants:
        PRIVACY = 150
        SECURITY = 250
        DUPLICATE = 6
        AFFECTED_USER = 4
        SUBSCRIBER = 2

    def get_max_heat_for_bug(bug_id):
        results = plpy.execute("""
            SELECT MAX(
                GREATEST(Product.max_bug_heat,
                         DistributionSourcePackage.max_bug_heat))
                    AS max_heat
            FROM BugTask
            LEFT OUTER JOIN ProductSeries ON
                BugTask.productseries = ProductSeries.id
            LEFT OUTER JOIN Product ON (
                BugTask.product = Product.id
                OR ProductSeries.product = Product.id)
            LEFT OUTER JOIN DistroSeries ON
                BugTask.distroseries = DistroSeries.id
            LEFT OUTER JOIN Distribution ON (
                BugTask.distribution = Distribution.id
                OR DistroSeries.distribution = Distribution.id)
            LEFT OUTER JOIN DistributionSourcePackage ON (
                BugTask.sourcepackagename =
                    DistributionSourcePackage.sourcepackagename)
            WHERE
                BugTask.bug = %s""" % bug_id)

        return results[0]['max_heat']

    # It would be nice to be able to just SELECT * here, but we need the
    # timestamps to be in a format that datetime.fromtimestamp() will
    # understand.
    bug_data = plpy.execute("""
        SELECT
            duplicateof,
            private,
            security_related,
            number_of_duplicates,
            users_affected_count,
            EXTRACT(epoch from datecreated)
                AS timestamp_date_created,
            EXTRACT(epoch from date_last_updated)
                AS timestamp_date_last_updated,
            EXTRACT(epoch from date_last_message)
                AS timestamp_date_last_message
        FROM Bug WHERE id = %s""" % bug_id)

    if bug_data.nrows() == 0:
        raise Exception("Bug %s doesn't exist." % bug_id)

    bug = bug_data[0]
    if bug['duplicateof'] is not None:
        return None

    heat = {}
    heat['dupes'] = (
        BugHeatConstants.DUPLICATE * bug['number_of_duplicates'])
    heat['affected_users'] = (
        BugHeatConstants.AFFECTED_USER *
        bug['users_affected_count'])

    if bug['private']:
        heat['privacy'] = BugHeatConstants.PRIVACY
    if bug['security_related']:
        heat['security'] = BugHeatConstants.SECURITY

    # Get the heat from subscribers, both direct and via duplicates.
    subs_from_dupes = plpy.execute("""
        SELECT COUNT(DISTINCT BugSubscription.person) AS sub_count
        FROM BugSubscription, Bug
        WHERE Bug.id = BugSubscription.bug
            AND (Bug.id = %s OR Bug.duplicateof = %s)"""
        % (bug_id, bug_id))

    heat['subcribers'] = (
        BugHeatConstants.SUBSCRIBER
        * subs_from_dupes[0]['sub_count'])

    total_heat = sum(heat.values())

    # Bugs decay over time. Every day the bug isn't touched its heat
    # decreases by 1%.
    date_last_updated = datetime.fromtimestamp(
        bug['timestamp_date_last_updated'])
    days_since_last_update = (datetime.utcnow() - date_last_updated).days
    total_heat = int(total_heat * (0.99 ** days_since_last_update))

    if days_since_last_update > 0:
        # Bug heat increases by a quarter of the maximum bug heat
        # divided by the number of days since the bug's creation date.
        date_created = datetime.fromtimestamp(
            bug['timestamp_date_created'])

        if bug['timestamp_date_last_message'] is not None:
            date_last_message = datetime.fromtimestamp(
                bug['timestamp_date_last_message'])
            oldest_date = max(date_last_updated, date_last_message)
        else:
            date_last_message = None
            oldest_date = date_last_updated

        days_since_last_activity = (datetime.utcnow() - oldest_date).days
        days_since_created = (datetime.utcnow() - date_created).days
        max_heat = get_max_heat_for_bug(bug_id)
        if max_heat is not None and days_since_created > 0:
            total_heat = (
                total_heat + (max_heat * 0.25 / days_since_created))

    return int(total_heat)
$$;

CREATE OR REPLACE FUNCTION bugmessage_copy_owner_from_message()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.owner is NULL THEN
            UPDATE BugMessage
            SET owner = Message.owner FROM
            Message WHERE
            Message.id = NEW.message AND
            BugMessage.id = NEW.id;
        END IF;
    ELSIF NEW.message != OLD.message THEN
        UPDATE BugMessage
        SET owner = Message.owner FROM
        Message WHERE
        Message.id = NEW.message AND
        BugMessage.id = NEW.id;
    END IF;
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION bugmessage_copy_owner_from_message() IS
'Copies the message owner into bugmessage when bugmessage changes.';

CREATE OR REPLACE FUNCTION message_copy_owner_to_bugmessage()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF NEW.owner != OLD.owner THEN
        UPDATE BugMessage
        SET owner = NEW.owner
        WHERE
        BugMessage.message = NEW.id;
    END IF;
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION message_copy_owner_to_bugmessage() IS
'Copies the message owner into bugmessage when message changes.';


CREATE OR REPLACE FUNCTION questionmessage_copy_owner_from_message()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.owner is NULL THEN
            UPDATE QuestionMessage
            SET owner = Message.owner FROM
            Message WHERE
            Message.id = NEW.message AND
            QuestionMessage.id = NEW.id;
        END IF;
    ELSIF NEW.message != OLD.message THEN
        UPDATE QuestionMessage
        SET owner = Message.owner FROM
        Message WHERE
        Message.id = NEW.message AND
        QuestionMessage.id = NEW.id;
    END IF;
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION questionmessage_copy_owner_from_message() IS
'Copies the message owner into QuestionMessage when QuestionMessage changes.';

CREATE OR REPLACE FUNCTION message_copy_owner_to_questionmessage()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF NEW.owner != OLD.owner THEN
        UPDATE QuestionMessage
        SET owner = NEW.owner
        WHERE
        QuestionMessage.message = NEW.id;
    END IF;
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION message_copy_owner_to_questionmessage() IS
'Copies the message owner into questionmessage when message changes.';


CREATE OR REPLACE FUNCTION bug_update_heat_copy_to_bugtask()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    IF NEW.heat != OLD.heat THEN
        UPDATE bugtask SET heat=NEW.heat WHERE bugtask.bug=NEW.id;
    END IF;
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION bug_update_heat_copy_to_bugtask() IS
'Copies bug heat to bugtasks when the bug is changed. Runs on UPDATE only because INSERTs do not have bugtasks at the point of insertion.';

-- This function is not STRICT, since it needs to handle
-- dateexpected when it is NULL.
CREATE OR REPLACE FUNCTION milestone_sort_key(
    dateexpected timestamp, name text)
    RETURNS text
AS $_$
    # If this method is altered, then any functional indexes using it
    # need to be rebuilt.
    import re
    import datetime

    date_expected, name = args

    def substitute_filled_numbers(match):
        return match.group(0).zfill(5)

    name = re.sub(u'\d+', substitute_filled_numbers, name)
    if date_expected is None:
        # NULL dates are considered to be in the future.
        date_expected = datetime.datetime(datetime.MAXYEAR, 1, 1)
    return '%s %s' % (date_expected, name)
$_$
LANGUAGE plpythonu IMMUTABLE;

COMMENT ON FUNCTION milestone_sort_key(timestamp, text) IS
'Sort by the Milestone dateexpected and name. If the dateexpected is NULL, then it is converted to a date far in the future, so it will be sorted as a milestone in the future.';


CREATE OR REPLACE FUNCTION version_sort_key(version text) RETURNS text
LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT AS
$$
    # If this method is altered, then any functional indexes using it
    # need to be rebuilt.
    import re

    [version] = args

    def substitute_filled_numbers(match):
        # Prepend "~" so that version numbers will show up first
        # when sorted descending, i.e. [3, 2c, 2b, 1, c, b, a] instead
        # of [c, b, a, 3, 2c, 2b, 1]. "~" has the highest ASCII value
        # of visible ASCII characters.
        return '~' + match.group(0).zfill(5)

    return re.sub(u'\d+', substitute_filled_numbers, version)
$$;

COMMENT ON FUNCTION version_sort_key(text) IS
'Sort a field as version numbers that do not necessarily conform to debian package versions (For example, when "2-2" should be considered greater than "1:1"). debversion_sort_key() should be used for debian versions. Numbers will be sorted after letters unlike typical ASCII, so that a descending sort will put the latest version number that starts with a number instead of a letter will be at the top. E.g. ascending is [a, z, 1, 9] and descending is [9, 1, z, a].';

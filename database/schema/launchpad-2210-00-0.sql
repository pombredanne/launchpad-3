-- Generated Mon Feb 25 21:35:23 2019 UTC

SET client_min_messages TO ERROR;
SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

CREATE SCHEMA todrop;


CREATE SCHEMA trgm;


CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


CREATE EXTENSION IF NOT EXISTS plpythonu WITH SCHEMA pg_catalog;


COMMENT ON EXTENSION plpythonu IS 'PL/PythonU untrusted procedural language';


CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA trgm;


COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


CREATE EXTENSION IF NOT EXISTS pgstattuple WITH SCHEMA public;


COMMENT ON EXTENSION pgstattuple IS 'show tuple-level statistics';


CREATE TYPE public.debversion;


CREATE FUNCTION public.debversionin(cstring) RETURNS public.debversion
    LANGUAGE internal IMMUTABLE STRICT
    AS $$textin$$;


CREATE FUNCTION public.debversionout(public.debversion) RETURNS cstring
    LANGUAGE internal IMMUTABLE STRICT
    AS $$textout$$;


CREATE FUNCTION public.debversionrecv(internal) RETURNS public.debversion
    LANGUAGE internal STABLE STRICT
    AS $$textrecv$$;


CREATE FUNCTION public.debversionsend(public.debversion) RETURNS bytea
    LANGUAGE internal STABLE STRICT
    AS $$textsend$$;


CREATE TYPE public.debversion (
    INTERNALLENGTH = variable,
    INPUT = public.debversionin,
    OUTPUT = public.debversionout,
    RECEIVE = public.debversionrecv,
    SEND = public.debversionsend,
    CATEGORY = 'S',
    ALIGNMENT = int4,
    STORAGE = extended
);


COMMENT ON TYPE public.debversion IS 'Debian package version number';


CREATE TYPE public.pgstattuple_type AS (
	table_len bigint,
	tuple_count bigint,
	tuple_len bigint,
	tuple_percent double precision,
	dead_tuple_count bigint,
	dead_tuple_len bigint,
	dead_tuple_percent double precision,
	free_space bigint,
	free_percent double precision
);


CREATE DOMAIN public.ts2_tsvector AS tsvector;


CREATE FUNCTION public._ftq(text) RETURNS text
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


CREATE FUNCTION public.accessartifact_denorm_to_artifacts(artifact_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    artifact_row accessartifact%ROWTYPE;
BEGIN
    SELECT * INTO artifact_row FROM accessartifact WHERE id = artifact_id;
    IF artifact_row.bug IS NOT NULL THEN
        PERFORM bug_flatten_access(artifact_row.bug);
    END IF;
    IF artifact_row.branch IS NOT NULL THEN
        PERFORM branch_denorm_access(artifact_row.branch);
    END IF;
    IF artifact_row.gitrepository IS NOT NULL THEN
        PERFORM gitrepository_denorm_access(artifact_row.gitrepository);
    END IF;
    IF artifact_row.specification IS NOT NULL THEN
        PERFORM specification_denorm_access(artifact_row.specification);
    END IF;
    RETURN;
END;
$$;


COMMENT ON FUNCTION public.accessartifact_denorm_to_artifacts(artifact_id integer) IS 'Denormalize the policy access and artifact grants to bugs, branches, Git repositories, and specifications.';


CREATE FUNCTION public.accessartifact_maintain_denorm_to_artifacts_trig() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM accessartifact_denorm_to_artifacts(NEW.artifact);
    ELSIF TG_OP = 'UPDATE' THEN
        PERFORM accessartifact_denorm_to_artifacts(NEW.artifact);
        IF OLD.artifact != NEW.artifact THEN
            PERFORM accessartifact_denorm_to_artifacts(OLD.artifact);
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM accessartifact_denorm_to_artifacts(OLD.artifact);
    END IF;
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.accessartifactgrant_maintain_accesspolicygrantflat_trig() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO AccessPolicyGrantFlat
            (policy, artifact, grantee)
            SELECT policy, NEW.artifact, NEW.grantee
                FROM AccessPolicyArtifact WHERE artifact = NEW.artifact;
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.artifact != OLD.artifact OR NEW.grantee != OLD.grantee THEN
            UPDATE AccessPolicyGrantFlat
                SET artifact=NEW.artifact, grantee=NEW.grantee
                WHERE artifact = OLD.artifact AND grantee = OLD.grantee;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        DELETE FROM AccessPolicyGrantFlat
            WHERE artifact = OLD.artifact AND grantee = OLD.grantee;
    END IF;
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.accesspolicyartifact_maintain_accesspolicyartifactflat_trig() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO AccessPolicyGrantFlat
            (policy, artifact, grantee)
            SELECT NEW.policy, NEW.artifact, grantee
                FROM AccessArtifactGrant WHERE artifact = NEW.artifact;
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.policy != OLD.policy OR NEW.artifact != OLD.artifact THEN
            UPDATE AccessPolicyGrantFlat
                SET policy=NEW.policy, artifact=NEW.artifact
                WHERE policy = OLD.policy AND artifact = OLD.artifact;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        DELETE FROM AccessPolicyGrantFlat
            WHERE policy = OLD.policy AND artifact = OLD.artifact;
    END IF;
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.accesspolicygrant_maintain_accesspolicygrantflat_trig() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO AccessPolicyGrantFlat
            (policy, grantee) VALUES (NEW.policy, NEW.grantee);
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.policy != OLD.policy OR NEW.grantee != OLD.grantee THEN
            UPDATE AccessPolicyGrantFlat
                SET policy=NEW.policy, grantee=NEW.grantee
                WHERE
                    policy = OLD.policy
                    AND grantee = OLD.grantee
                    AND artifact IS NULL;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        DELETE FROM AccessPolicyGrantFlat
            WHERE
                policy = OLD.policy
                AND grantee = OLD.grantee
                AND artifact IS NULL;
    END IF;
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.activity() RETURNS SETOF pg_stat_activity
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
DECLARE
    a pg_stat_activity%ROWTYPE;
BEGIN
    IF EXISTS (
            SELECT 1 FROM pg_attribute WHERE
                attrelid =
                    (SELECT oid FROM pg_class
                     WHERE relname = 'pg_stat_activity')
                AND attname = 'backend_type') THEN
        -- >= 10
        RETURN QUERY SELECT
            datid, datname, pid, usesysid, usename, application_name,
            client_addr, client_hostname, client_port, backend_start,
            xact_start, query_start, state_change, wait_event_type,
            wait_event, state, backend_xid, backend_xmin, backend_type,
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


COMMENT ON FUNCTION public.activity() IS 'SECURITY DEFINER wrapper around pg_stat_activity allowing unprivileged users to access most of its information.';


CREATE FUNCTION public.add_test_openid_identifier(account_ integer) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.add_test_openid_identifier(account_ integer) IS 'Add an OpenIdIdentifier to an account that can be used to login in the test environment. These identifiers are not usable on production or staging.';


CREATE FUNCTION public.assert_patch_applied(major integer, minor integer, patch integer) RETURNS boolean
    LANGUAGE plpythonu STABLE
    AS $$
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


COMMENT ON FUNCTION public.assert_patch_applied(major integer, minor integer, patch integer) IS 'Raise an exception if the given database patch has not been applied.';


CREATE FUNCTION public.branch_denorm_access(branch_id integer) RETURNS void
    LANGUAGE sql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
    UPDATE branch
        SET access_policy = policies[1], access_grants = grants
        FROM
            build_access_cache(
                (SELECT id FROM accessartifact WHERE branch = $1),
                (SELECT information_type FROM branch WHERE id = $1))
            AS (policies integer[], grants integer[])
        WHERE id = $1;
$_$;


CREATE FUNCTION public.branch_maintain_access_cache_trig() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM branch_denorm_access(NEW.id);
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.bug_build_access_cache(bug_id integer, information_type integer) RETURNS record
    LANGUAGE sql
    AS $_$
    SELECT build_access_cache(
        (SELECT id FROM accessartifact WHERE bug = $1), $2);
$_$;


COMMENT ON FUNCTION public.bug_build_access_cache(bug_id integer, information_type integer) IS 'Build an access cache for the given bug. Returns ({AccessPolicyArtifact.policy}, {AccessArtifactGrant.grantee}) for private bugs, or (NULL, NULL) for public ones.';


CREATE FUNCTION public.bug_flatten_access(bug_id integer) RETURNS void
    LANGUAGE sql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
    UPDATE bugtaskflat
        SET access_policies = policies, access_grants = grants
        FROM
            build_access_cache(
                (SELECT id FROM accessartifact WHERE bug = $1),
                (SELECT information_type FROM bug WHERE id = $1))
            AS (policies integer[], grants integer[])
        WHERE bug = $1;
$_$;


COMMENT ON FUNCTION public.bug_flatten_access(bug_id integer) IS 'Recalculate the access cache on a bug''s flattened tasks.';


CREATE FUNCTION public.bug_maintain_bugtaskflat_trig() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    IF (
        NEW.duplicateof IS DISTINCT FROM OLD.duplicateof
        OR NEW.owner IS DISTINCT FROM OLD.owner
        OR NEW.fti IS DISTINCT FROM OLD.fti
        OR NEW.information_type IS DISTINCT FROM OLD.information_type
        OR NEW.date_last_updated IS DISTINCT FROM OLD.date_last_updated
        OR NEW.heat IS DISTINCT FROM OLD.heat
        OR NEW.latest_patch_uploaded IS DISTINCT FROM
            OLD.latest_patch_uploaded) THEN
        UPDATE bugtaskflat
            SET
                duplicateof = NEW.duplicateof,
                bug_owner = NEW.owner,
                fti = NEW.fti,
                information_type = NEW.information_type,
                date_last_updated = NEW.date_last_updated,
                heat = NEW.heat,
                latest_patch_uploaded = NEW.latest_patch_uploaded
            WHERE bug = OLD.id;
    END IF;

    IF NEW.information_type IS DISTINCT FROM OLD.information_type THEN
        PERFORM bug_flatten_access(OLD.id);
    END IF;
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.valid_bug_name(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $_$
    import re
    name = args[0]
    pat = r"^[a-z][a-z0-9+\.\-]+$"
    if re.match(pat, name):
        return 1
    return 0
$_$;


COMMENT ON FUNCTION public.valid_bug_name(text) IS 'validate a bug name

    As per valid_name, except numeric-only names are not allowed (including
    names that look like floats).';


SET default_tablespace = '';

SET default_with_oids = false;

CREATE TABLE public.bug (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    name text,
    title text NOT NULL,
    description text NOT NULL,
    owner integer NOT NULL,
    duplicateof integer,
    fti public.ts2_tsvector,
    date_last_updated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_made_private timestamp without time zone,
    who_made_private integer,
    date_last_message timestamp without time zone,
    number_of_duplicates integer DEFAULT 0 NOT NULL,
    message_count integer DEFAULT 0 NOT NULL,
    users_affected_count integer DEFAULT 0,
    users_unaffected_count integer DEFAULT 0,
    heat integer DEFAULT 0 NOT NULL,
    heat_last_updated timestamp without time zone,
    latest_patch_uploaded timestamp without time zone,
    information_type integer NOT NULL,
    CONSTRAINT notduplicateofself CHECK ((NOT (id = duplicateof))),
    CONSTRAINT sane_description CHECK (((ltrim(description) <> ''::text) AND (char_length(description) <= 50000))),
    CONSTRAINT valid_bug_name CHECK (public.valid_bug_name(name))
);


COMMENT ON TABLE public.bug IS 'A software bug that requires fixing. This particular bug may be linked to one or more products or source packages to identify the location(s) that this bug is found.';


COMMENT ON COLUMN public.bug.name IS 'A lowercase name uniquely identifying the bug';


COMMENT ON COLUMN public.bug.description IS 'A detailed description of the bug. Initially this will be set to the contents of the initial email or bug filing comment, but later it can be edited to give a more accurate description of the bug itself rather than the symptoms observed by the reporter.';


COMMENT ON COLUMN public.bug.date_last_message IS 'When the last BugMessage was attached to this Bug. Maintained by a trigger on the BugMessage table.';


COMMENT ON COLUMN public.bug.number_of_duplicates IS 'The number of bugs marked as duplicates of this bug, populated by a trigger after setting the duplicateof of bugs.';


COMMENT ON COLUMN public.bug.message_count IS 'The number of messages (currently just comments) on this bugbug, maintained by the set_bug_message_count_t trigger.';


COMMENT ON COLUMN public.bug.users_affected_count IS 'The number of users affected by this bug, maintained by the set_bug_users_affected_count_t trigger.';


COMMENT ON COLUMN public.bug.heat IS 'The relevance of this bug. This value is computed periodically using bug_affects_person and other bug values.';


COMMENT ON COLUMN public.bug.heat_last_updated IS 'The time this bug''s heat was last updated, or NULL if the heat has never yet been updated.';


COMMENT ON COLUMN public.bug.latest_patch_uploaded IS 'The time when the most recent patch has been attached to this bug or NULL if no patches are attached';


COMMENT ON COLUMN public.bug.information_type IS 'Enum describing what type of information is stored, such as type of private or security related data, and used to determine how to apply an access policy.';


CREATE FUNCTION public.bug_row(bug_id integer) RETURNS public.bug
    LANGUAGE sql STABLE
    AS $_$
    SELECT * FROM Bug WHERE id=$1;
$_$;


COMMENT ON FUNCTION public.bug_row(bug_id integer) IS 'Helper for manually testing functions requiring a bug row as input. eg. SELECT * FROM bugsummary_tags(bug_row(1))';


CREATE TABLE public.bugsummary (
    id integer NOT NULL,
    count integer DEFAULT 0 NOT NULL,
    product integer,
    productseries integer,
    distribution integer,
    distroseries integer,
    sourcepackagename integer,
    viewed_by integer,
    tag text,
    status integer NOT NULL,
    milestone integer,
    importance integer NOT NULL,
    has_patch boolean NOT NULL,
    access_policy integer,
    CONSTRAINT bugtask_assignment_checks CHECK (
CASE
    WHEN (product IS NOT NULL) THEN ((((productseries IS NULL) AND (distribution IS NULL)) AND (distroseries IS NULL)) AND (sourcepackagename IS NULL))
    WHEN (productseries IS NOT NULL) THEN (((distribution IS NULL) AND (distroseries IS NULL)) AND (sourcepackagename IS NULL))
    WHEN (distribution IS NOT NULL) THEN (distroseries IS NULL)
    WHEN (distroseries IS NOT NULL) THEN true
    ELSE false
END)
);


COMMENT ON TABLE public.bugsummary IS 'A fact table for bug metadata aggregate queries. Each row represents the number of bugs that are in the system addressed by all the dimensions (e.g. product or productseries etc). ';


COMMENT ON COLUMN public.bugsummary.sourcepackagename IS 'The sourcepackagename for the aggregate. Counting bugs in a distribution/distroseries requires selecting all rows by sourcepackagename. If this is too slow, add the bug to the NULL row and select with sourcepackagename is NULL to exclude them from the calculations';


COMMENT ON COLUMN public.bugsummary.milestone IS 'A milestone present on the bug. All bugs are also aggregated with a NULL entry for milestone to permit querying totals (because the milestone figures cannot be summed as many milestones can be on a single bug)';


CREATE FUNCTION public.bug_summary_dec(public.bugsummary) RETURNS void
    LANGUAGE sql
    AS $_$
    -- We own the row reference, so in the absence of bugs this cannot
    -- fail - just decrement the row.
    UPDATE BugSummary SET count = count + $1.count
    WHERE
        ((product IS NULL AND $1.product IS NULL)
            OR product = $1.product)
        AND ((productseries IS NULL AND $1.productseries IS NULL)
            OR productseries = $1.productseries)
        AND ((distribution IS NULL AND $1.distribution IS NULL)
            OR distribution = $1.distribution)
        AND ((distroseries IS NULL AND $1.distroseries IS NULL)
            OR distroseries = $1.distroseries)
        AND ((sourcepackagename IS NULL AND $1.sourcepackagename IS NULL)
            OR sourcepackagename = $1.sourcepackagename)
        AND ((viewed_by IS NULL AND $1.viewed_by IS NULL)
            OR viewed_by = $1.viewed_by)
        AND ((tag IS NULL AND $1.tag IS NULL)
            OR tag = $1.tag)
        AND status = $1.status
        AND ((milestone IS NULL AND $1.milestone IS NULL)
            OR milestone = $1.milestone)
        AND importance = $1.importance
        AND has_patch = $1.has_patch
        AND access_policy IS NOT DISTINCT FROM $1.access_policy;
$_$;


COMMENT ON FUNCTION public.bug_summary_dec(public.bugsummary) IS 'UPSERT into bugsummary incrementing one row';


CREATE FUNCTION public.bug_summary_flush_temp_journal() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    d bugsummary%ROWTYPE;
BEGIN
    -- May get called even though no summaries were made (for simplicity in the
    -- callers). We sum the rows here to minimise the number of inserts
    -- into the persistent journal, as it's reasonably likely that we'll
    -- have -1s and +1s cancelling each other out.
    PERFORM ensure_bugsummary_temp_journal();
    INSERT INTO BugSummaryJournal(
        count, product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone, importance, has_patch, access_policy)
    SELECT
        SUM(count), product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone, importance, has_patch, access_policy
    FROM bugsummary_temp_journal
    GROUP BY
        product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone, importance, has_patch, access_policy
    HAVING SUM(count) != 0;
    TRUNCATE bugsummary_temp_journal;
END;
$$;


COMMENT ON FUNCTION public.bug_summary_flush_temp_journal() IS 'flush the temporary bugsummary journal into the bugsummary table';


CREATE FUNCTION public.bug_summary_inc(d public.bugsummary) RETURNS void
    LANGUAGE plpgsql
    AS $_$
BEGIN
    -- Shameless adaption from postgresql manual
    LOOP
        -- first try to update the row
        UPDATE BugSummary SET count = count + d.count
        WHERE
            ((product IS NULL AND $1.product IS NULL)
                OR product = $1.product)
            AND ((productseries IS NULL AND $1.productseries IS NULL)
                OR productseries = $1.productseries)
            AND ((distribution IS NULL AND $1.distribution IS NULL)
                OR distribution = $1.distribution)
            AND ((distroseries IS NULL AND $1.distroseries IS NULL)
                OR distroseries = $1.distroseries)
            AND ((sourcepackagename IS NULL AND $1.sourcepackagename IS NULL)
                OR sourcepackagename = $1.sourcepackagename)
            AND ((viewed_by IS NULL AND $1.viewed_by IS NULL)
                OR viewed_by = $1.viewed_by)
            AND ((tag IS NULL AND $1.tag IS NULL)
                OR tag = $1.tag)
            AND status = $1.status
            AND ((milestone IS NULL AND $1.milestone IS NULL)
                OR milestone = $1.milestone)
            AND importance = $1.importance
            AND has_patch = $1.has_patch
            AND access_policy IS NOT DISTINCT FROM $1.access_policy;
        IF found THEN
            RETURN;
        END IF;
        -- not there, so try to insert the key
        -- if someone else inserts the same key concurrently,
        -- we could get a unique-key failure
        BEGIN
            INSERT INTO BugSummary(
                count, product, productseries, distribution,
                distroseries, sourcepackagename, viewed_by, tag,
                status, milestone, importance, has_patch, access_policy)
            VALUES (
                d.count, d.product, d.productseries, d.distribution,
                d.distroseries, d.sourcepackagename, d.viewed_by, d.tag,
                d.status, d.milestone, d.importance, d.has_patch,
                d.access_policy);
            RETURN;
        EXCEPTION WHEN unique_violation THEN
            -- do nothing, and loop to try the UPDATE again
        END;
    END LOOP;
END;
$_$;


COMMENT ON FUNCTION public.bug_summary_inc(d public.bugsummary) IS 'UPSERT into bugsummary incrementing one row';


CREATE FUNCTION public.bug_update_latest_patch_uploaded(integer) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
BEGIN
    UPDATE bug SET latest_patch_uploaded =
        (SELECT max(message.datecreated)
            FROM message, bugattachment
            WHERE bugattachment.message=message.id AND
                bugattachment.bug=$1 AND
                bugattachment.type=1)
        WHERE bug.id=$1;
END;
$_$;


CREATE FUNCTION public.bug_update_latest_patch_uploaded_on_delete() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    PERFORM bug_update_latest_patch_uploaded(OLD.bug);
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;


CREATE FUNCTION public.bug_update_latest_patch_uploaded_on_insert_update() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    PERFORM bug_update_latest_patch_uploaded(NEW.bug);
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;


CREATE FUNCTION public.bugmessage_copy_owner_from_message() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.bugmessage_copy_owner_from_message() IS 'Copies the message owner into bugmessage when bugmessage changes.';


CREATE FUNCTION public.bugsummary_journal_bug(bug_row public.bug, _count integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    btf_row bugtaskflat%ROWTYPE;
BEGIN
    FOR btf_row IN SELECT * FROM bugtaskflat WHERE bug = bug_row.id
    LOOP
        PERFORM bugsummary_journal_bugtaskflat(btf_row, _count);
    END LOOP;
END;
$$;


CREATE TABLE public.bugtaskflat (
    bugtask integer NOT NULL,
    bug integer NOT NULL,
    datecreated timestamp without time zone,
    duplicateof integer,
    bug_owner integer NOT NULL,
    fti public.ts2_tsvector,
    information_type integer NOT NULL,
    date_last_updated timestamp without time zone NOT NULL,
    heat integer NOT NULL,
    product integer,
    productseries integer,
    distribution integer,
    distroseries integer,
    sourcepackagename integer,
    status integer NOT NULL,
    importance integer NOT NULL,
    assignee integer,
    milestone integer,
    owner integer NOT NULL,
    active boolean NOT NULL,
    access_policies integer[],
    access_grants integer[],
    latest_patch_uploaded timestamp without time zone,
    date_closed timestamp without time zone
);


CREATE FUNCTION public.bugsummary_journal_bugtaskflat(btf_row public.bugtaskflat, _count integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM ensure_bugsummary_temp_journal();
    INSERT INTO BugSummary_Temp_Journal(
        count, product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone, importance, has_patch, access_policy)
    SELECT
        _count, product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone, importance, has_patch, access_policy
        FROM bugsummary_locations(btf_row);
END;
$$;


CREATE FUNCTION public.bugsummary_locations(btf_row public.bugtaskflat) RETURNS SETOF public.bugsummary
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF btf_row.duplicateof IS NOT NULL THEN
        RETURN;
    END IF;
    RETURN QUERY
        SELECT
            CAST(NULL AS integer) AS id,
            CAST(1 AS integer) AS count,
            bug_targets.product, bug_targets.productseries,
            bug_targets.distribution, bug_targets.distroseries,
            bug_targets.sourcepackagename,
            bug_viewers.viewed_by, bug_tags.tag, btf_row.status,
            btf_row.milestone, btf_row.importance,
            btf_row.latest_patch_uploaded IS NOT NULL AS has_patch,
            bug_viewers.access_policy
        FROM
            bugsummary_targets(btf_row) as bug_targets,
            bugsummary_tags(btf_row) AS bug_tags,
            bugsummary_viewers(btf_row) AS bug_viewers;
END;
$$;


CREATE FUNCTION public.bugsummary_rollup_journal(batchsize integer DEFAULT NULL::integer) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
DECLARE
    d bugsummary%ROWTYPE;
    max_id integer;
BEGIN
    -- Lock so we don't content with other invokations of this
    -- function. We can happily lock the BugSummary table for writes
    -- as this function is the only thing that updates that table.
    -- BugSummaryJournal remains unlocked so nothing should be blocked.
    LOCK TABLE BugSummary IN ROW EXCLUSIVE MODE;

    IF batchsize IS NULL THEN
        SELECT MAX(id) INTO max_id FROM BugSummaryJournal;
    ELSE
        SELECT MAX(id) INTO max_id FROM (
            SELECT id FROM BugSummaryJournal ORDER BY id LIMIT batchsize
            ) AS Whatever;
    END IF;

    FOR d IN
        SELECT
            NULL as id,
            SUM(count),
            product,
            productseries,
            distribution,
            distroseries,
            sourcepackagename,
            viewed_by,
            tag,
            status,
            milestone,
            importance,
            has_patch,
            access_policy
        FROM BugSummaryJournal
        WHERE id <= max_id
        GROUP BY
            product, productseries, distribution, distroseries,
            sourcepackagename, viewed_by, tag, status, milestone,
            importance, has_patch, access_policy
        HAVING sum(count) <> 0
    LOOP
        IF d.count < 0 THEN
            PERFORM bug_summary_dec(d);
        ELSIF d.count > 0 THEN
            PERFORM bug_summary_inc(d);
        END IF;
    END LOOP;

    -- Clean out any counts we reduced to 0.
    DELETE FROM BugSummary WHERE count=0;
    -- Clean out the journal entries we have handled.
    DELETE FROM BugSummaryJournal WHERE id <= max_id;
END;
$$;


COMMENT ON FUNCTION public.bugsummary_rollup_journal(batchsize integer) IS 'Collate and migrate rows from BugSummaryJournal to BugSummary';


CREATE FUNCTION public.valid_name(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
    import re
    name = args[0]
    pat = r"^[a-z0-9][a-z0-9\+\.\-]*\Z"
    if re.match(pat, name):
        return 1
    return 0
$$;


COMMENT ON FUNCTION public.valid_name(text) IS 'validate a name.

    Names must contain only lowercase letters, numbers, ., & -. They
    must start with an alphanumeric. They are ASCII only. Names are useful
    for mneumonic identifiers such as nicknames and as URL components.
    This specification is the same as the Debian product naming policy.

    Note that a valid name might be all integers, so there is a possible
    namespace conflict if URL traversal is possible by name as well as id.';


CREATE TABLE public.bugtag (
    id integer NOT NULL,
    bug integer NOT NULL,
    tag text NOT NULL,
    CONSTRAINT valid_tag CHECK (public.valid_name(tag))
);


COMMENT ON TABLE public.bugtag IS 'Attaches simple text tags to a bug.';


COMMENT ON COLUMN public.bugtag.bug IS 'The bug the tags is attached to.';


COMMENT ON COLUMN public.bugtag.tag IS 'The text representation of the tag.';


CREATE FUNCTION public.bugsummary_tags(btf_row public.bugtaskflat) RETURNS SETOF public.bugtag
    LANGUAGE sql STABLE
    AS $_$
    SELECT * FROM BugTag WHERE BugTag.bug = $1.bug
    UNION ALL
    SELECT NULL::integer, $1.bug, NULL::text;
$_$;


CREATE FUNCTION public.bugsummary_targets(btf_row public.bugtaskflat) RETURNS TABLE(product integer, productseries integer, distribution integer, distroseries integer, sourcepackagename integer)
    LANGUAGE sql IMMUTABLE
    AS $_$
    -- Include a sourcepackagename-free task if this one has a
    -- sourcepackagename, so package tasks are also counted in their
    -- distro/series.
    SELECT
        $1.product, $1.productseries, $1.distribution,
        $1.distroseries, $1.sourcepackagename
    UNION -- Implicit DISTINCT
    SELECT
        $1.product, $1.productseries, $1.distribution,
        $1.distroseries, NULL;
$_$;


CREATE FUNCTION public.bugsummary_viewers(btf_row public.bugtaskflat) RETURNS TABLE(viewed_by integer, access_policy integer)
    LANGUAGE sql IMMUTABLE
    AS $_$
    SELECT NULL::integer, NULL::integer WHERE $1.information_type IN (1, 2)
    UNION ALL
    SELECT unnest($1.access_grants), NULL::integer
    WHERE $1.information_type NOT IN (1, 2)
    UNION ALL
    SELECT NULL::integer, unnest($1.access_policies)
    WHERE $1.information_type NOT IN (1, 2);
$_$;


CREATE FUNCTION public.bugtag_maintain_bug_summary() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(NEW.bug);
        ELSE
            PERFORM summarise_bug(NEW.bug);
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(OLD.bug);
        ELSE
            PERFORM summarise_bug(OLD.bug);
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN OLD;
    ELSE
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(OLD.bug);
            IF OLD.bug <> NEW.bug THEN
                PERFORM unsummarise_bug(NEW.bug);
            END IF;
        ELSE
            PERFORM summarise_bug(OLD.bug);
            IF OLD.bug <> NEW.bug THEN
                PERFORM summarise_bug(NEW.bug);
            END IF;
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN NEW;
    END IF;
END;
$$;


COMMENT ON FUNCTION public.bugtag_maintain_bug_summary() IS 'AFTER trigger on bugtag maintaining the bugs summaries in bugsummary.';


CREATE FUNCTION public.bugtask_flatten(task_id integer, check_only boolean) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
DECLARE
    bug_row Bug%ROWTYPE;
    task_row BugTask%ROWTYPE;
    old_flat_row BugTaskFlat%ROWTYPE;
    new_flat_row BugTaskFlat%ROWTYPE;
    _product_active boolean;
    _access_policies integer[];
    _access_grants integer[];
BEGIN
    -- This is the master function to update BugTaskFlat, but there are
    -- maintenance triggers and jobs on the involved tables that update
    -- it directly. Any changes here probably require a corresponding
    -- change in other trigger functions.

    SELECT * INTO task_row FROM BugTask WHERE id = task_id;
    SELECT * INTO old_flat_row FROM BugTaskFlat WHERE bugtask = task_id;

    -- If the task doesn't exist, ensure that there's no flat row.
    IF task_row.id IS NULL THEN
        IF old_flat_row.bugtask IS NOT NULL THEN
            IF NOT check_only THEN
                DELETE FROM BugTaskFlat WHERE bugtask = task_id;
            END IF;
            RETURN FALSE;
        ELSE
            RETURN TRUE;
        END IF;
    END IF;

    SELECT * FROM bug INTO bug_row WHERE id = task_row.bug;

    -- If it's a product(series) task, we must consult the active flag.
    IF task_row.product IS NOT NULL THEN
        SELECT product.active INTO _product_active
            FROM product WHERE product.id = task_row.product LIMIT 1;
    ELSIF task_row.productseries IS NOT NULL THEN
        SELECT product.active INTO _product_active
            FROM
                product
                JOIN productseries ON productseries.product = product.id
            WHERE productseries.id = task_row.productseries LIMIT 1;
    END IF;

    SELECT policies, grants
        INTO _access_policies, _access_grants
        FROM bug_build_access_cache(bug_row.id, bug_row.information_type)
            AS (policies integer[], grants integer[]);

    -- Compile the new flat row.
    SELECT task_row.id, bug_row.id, task_row.datecreated,
           bug_row.duplicateof, bug_row.owner, bug_row.fti,
           bug_row.information_type, bug_row.date_last_updated,
           bug_row.heat, task_row.product, task_row.productseries,
           task_row.distribution, task_row.distroseries,
           task_row.sourcepackagename, task_row.status,
           task_row.importance, task_row.assignee,
           task_row.milestone, task_row.owner,
           COALESCE(_product_active, TRUE),
           _access_policies,
           _access_grants,
           bug_row.latest_patch_uploaded, task_row.date_closed
           INTO new_flat_row;

    -- Calculate the necessary updates.
    IF old_flat_row.bugtask IS NULL THEN
        IF NOT check_only THEN
            INSERT INTO BugTaskFlat VALUES (new_flat_row.*);
        END IF;
        RETURN FALSE;
    ELSIF new_flat_row != old_flat_row THEN
        IF NOT check_only THEN
            UPDATE BugTaskFlat SET
                bug = new_flat_row.bug,
                datecreated = new_flat_row.datecreated,
                duplicateof = new_flat_row.duplicateof,
                bug_owner = new_flat_row.bug_owner,
                fti = new_flat_row.fti,
                information_type = new_flat_row.information_type,
                date_last_updated = new_flat_row.date_last_updated,
                heat = new_flat_row.heat,
                product = new_flat_row.product,
                productseries = new_flat_row.productseries,
                distribution = new_flat_row.distribution,
                distroseries = new_flat_row.distroseries,
                sourcepackagename = new_flat_row.sourcepackagename,
                status = new_flat_row.status,
                importance = new_flat_row.importance,
                assignee = new_flat_row.assignee,
                milestone = new_flat_row.milestone,
                owner = new_flat_row.owner,
                active = new_flat_row.active,
                access_policies = new_flat_row.access_policies,
                access_grants = new_flat_row.access_grants,
                date_closed = new_flat_row.date_closed,
                latest_patch_uploaded = new_flat_row.latest_patch_uploaded
                WHERE bugtask = new_flat_row.bugtask;
        END IF;
        RETURN FALSE;
    ELSE
        RETURN TRUE;
    END IF;
END;
$$;


COMMENT ON FUNCTION public.bugtask_flatten(task_id integer, check_only boolean) IS 'Create or update a BugTaskFlat row from the source tables. Returns whether the row was up to date. If check_only is true, the row is not brought up to date.';


CREATE FUNCTION public.bugtask_maintain_bugtaskflat_trig() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM bugtask_flatten(NEW.id, FALSE);
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.bug != OLD.bug THEN
            RAISE EXCEPTION 'cannot move bugtask to a different bug';
        ELSIF (NEW.product IS DISTINCT FROM OLD.product
            OR NEW.productseries IS DISTINCT FROM OLD.productseries) THEN
            -- product.active may differ. Do a full update.
            PERFORM bugtask_flatten(NEW.id, FALSE);
        ELSIF (
            NEW.datecreated IS DISTINCT FROM OLD.datecreated
            OR NEW.product IS DISTINCT FROM OLD.product
            OR NEW.productseries IS DISTINCT FROM OLD.productseries
            OR NEW.distribution IS DISTINCT FROM OLD.distribution
            OR NEW.distroseries IS DISTINCT FROM OLD.distroseries
            OR NEW.sourcepackagename IS DISTINCT FROM OLD.sourcepackagename
            OR NEW.status IS DISTINCT FROM OLD.status
            OR NEW.importance IS DISTINCT FROM OLD.importance
            OR NEW.assignee IS DISTINCT FROM OLD.assignee
            OR NEW.milestone IS DISTINCT FROM OLD.milestone
            OR NEW.owner IS DISTINCT FROM OLD.owner
            OR NEW.date_closed IS DISTINCT FROM OLD.date_closed) THEN
            -- Otherwise just update the columns from bugtask.
            -- Access policies and grants may have changed due to target
            -- transitions, but an earlier trigger will already have
            -- mirrored them to all relevant flat tasks.
            UPDATE BugTaskFlat SET
                datecreated = NEW.datecreated,
                product = NEW.product,
                productseries = NEW.productseries,
                distribution = NEW.distribution,
                distroseries = NEW.distroseries,
                sourcepackagename = NEW.sourcepackagename,
                status = NEW.status,
                importance = NEW.importance,
                assignee = NEW.assignee,
                milestone = NEW.milestone,
                owner = NEW.owner,
                date_closed = NEW.date_closed
                WHERE bugtask = NEW.id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM bugtask_flatten(OLD.id, FALSE);
    END IF;
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.bugtaskflat_maintain_bug_summary() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM bugsummary_journal_bugtaskflat(NEW, 1);
        PERFORM bug_summary_flush_temp_journal();
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM bugsummary_journal_bugtaskflat(OLD, -1);
        PERFORM bug_summary_flush_temp_journal();
    ELSIF
        NEW.product IS DISTINCT FROM OLD.product
        OR NEW.productseries IS DISTINCT FROM OLD.productseries
        OR NEW.distribution IS DISTINCT FROM OLD.distribution
        OR NEW.distroseries IS DISTINCT FROM OLD.distroseries
        OR NEW.sourcepackagename IS DISTINCT FROM OLD.sourcepackagename
        OR NEW.status IS DISTINCT FROM OLD.status
        OR NEW.milestone IS DISTINCT FROM OLD.milestone
        OR NEW.importance IS DISTINCT FROM OLD.importance
        OR NEW.latest_patch_uploaded IS DISTINCT FROM OLD.latest_patch_uploaded
        OR NEW.information_type IS DISTINCT FROM OLD.information_type
        OR NEW.access_grants IS DISTINCT FROM OLD.access_grants
        OR NEW.access_policies IS DISTINCT FROM OLD.access_policies
        OR NEW.duplicateof IS DISTINCT FROM OLD.duplicateof
    THEN
        PERFORM bugsummary_journal_bugtaskflat(OLD, -1);
        PERFORM bugsummary_journal_bugtaskflat(NEW, 1);
        PERFORM bug_summary_flush_temp_journal();
    END IF;
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.build_access_cache(art_id integer, information_type integer) RETURNS record
    LANGUAGE plpgsql
    AS $$
DECLARE
    _policies integer[];
    _grants integer[];
    cache record;
BEGIN
    -- If private, grab the access control information.
    -- If public, access_policies and access_grants are NULL.
    -- 3 == PRIVATESECURITY, 4 == USERDATA, 5 == PROPRIETARY
    -- 6 == EMBARGOED
    IF information_type NOT IN (1, 2) THEN
        SELECT COALESCE(array_agg(policy ORDER BY policy), ARRAY[]::integer[])
            INTO _policies FROM accesspolicyartifact WHERE artifact = art_id;
        SELECT COALESCE(array_agg(grantee ORDER BY grantee), ARRAY[]::integer[])
            INTO _grants FROM accessartifactgrant WHERE artifact = art_id;
    END IF;
    cache := (_policies, _grants);
    RETURN cache;
END;
$$;


CREATE FUNCTION public.calculate_bug_heat(bug_id integer) RETURNS integer
    LANGUAGE sql STABLE STRICT
    AS $_$
    SELECT
        (CASE information_type WHEN 1 THEN 0 WHEN 2 THEN 250
            WHEN 3 THEN 400 ELSE 150 END)
        + (number_of_duplicates * 6)
        + (users_affected_count * 4)
        + (
            SELECT COUNT(DISTINCT person) * 2 
            FROM BugSubscription
            JOIN Bug AS SubBug ON BugSubscription.bug = SubBug.id
            WHERE SubBug.id = $1 OR SubBug.duplicateof = $1)::integer AS heat
    FROM Bug WHERE Bug.id = $1;
$_$;


CREATE FUNCTION public.cursor_fetch(cur refcursor, n integer) RETURNS SETOF record
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.cursor_fetch(cur refcursor, n integer) IS 'Fetch the next n items from a cursor. Work around for not being able to use FETCH inside a SELECT statement.';


CREATE FUNCTION public.debversion(character) RETURNS public.debversion
    LANGUAGE internal IMMUTABLE STRICT
    AS $$rtrim1$$;


CREATE FUNCTION public.debversion_cmp(version1 public.debversion, version2 public.debversion) RETURNS integer
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_cmp';


COMMENT ON FUNCTION public.debversion_cmp(version1 public.debversion, version2 public.debversion) IS 'Compare Debian versions';


CREATE FUNCTION public.debversion_eq(version1 public.debversion, version2 public.debversion) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_eq';


COMMENT ON FUNCTION public.debversion_eq(version1 public.debversion, version2 public.debversion) IS 'debversion equal';


CREATE FUNCTION public.debversion_ge(version1 public.debversion, version2 public.debversion) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_ge';


COMMENT ON FUNCTION public.debversion_ge(version1 public.debversion, version2 public.debversion) IS 'debversion greater-than-or-equal';


CREATE FUNCTION public.debversion_gt(version1 public.debversion, version2 public.debversion) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_gt';


COMMENT ON FUNCTION public.debversion_gt(version1 public.debversion, version2 public.debversion) IS 'debversion greater-than';


CREATE FUNCTION public.debversion_hash(public.debversion) RETURNS integer
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_hash';


CREATE FUNCTION public.debversion_larger(version1 public.debversion, version2 public.debversion) RETURNS public.debversion
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_larger';


CREATE FUNCTION public.debversion_le(version1 public.debversion, version2 public.debversion) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_le';


COMMENT ON FUNCTION public.debversion_le(version1 public.debversion, version2 public.debversion) IS 'debversion less-than-or-equal';


CREATE FUNCTION public.debversion_lt(version1 public.debversion, version2 public.debversion) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_lt';


COMMENT ON FUNCTION public.debversion_lt(version1 public.debversion, version2 public.debversion) IS 'debversion less-than';


CREATE FUNCTION public.debversion_ne(version1 public.debversion, version2 public.debversion) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_ne';


COMMENT ON FUNCTION public.debversion_ne(version1 public.debversion, version2 public.debversion) IS 'debversion not equal';


CREATE FUNCTION public.debversion_smaller(version1 public.debversion, version2 public.debversion) RETURNS public.debversion
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/debversion', 'debversion_smaller';


CREATE FUNCTION public.debversion_sort_key(version text) RETURNS text
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $_$
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
$_$;


COMMENT ON FUNCTION public.debversion_sort_key(version text) IS 'Return a string suitable for sorting debian version strings on';


CREATE FUNCTION public.ensure_bugsummary_temp_journal() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    CREATE TEMPORARY TABLE bugsummary_temp_journal (
        LIKE bugsummary ) ON COMMIT DROP;
    ALTER TABLE bugsummary_temp_journal ALTER COLUMN id DROP NOT NULL;
EXCEPTION
    WHEN duplicate_table THEN
        NULL;
END;
$$;


COMMENT ON FUNCTION public.ensure_bugsummary_temp_journal() IS 'Create a temporary table bugsummary_temp_journal if it does not exist.';


CREATE FUNCTION public.ftiupdate() RETURNS trigger
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


COMMENT ON FUNCTION public.ftiupdate() IS 'Trigger function that keeps the fti tsvector column up to date.';


CREATE FUNCTION public.ftq(text) RETURNS tsquery
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $_$
        p = plpy.prepare(
            "SELECT to_tsquery('default', _ftq($1)) AS x", ["text"])
        query = plpy.execute(p, args, 1)[0]["x"]
        return query or None
        $_$;


CREATE FUNCTION public.getlocalnodeid() RETURNS integer
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.getlocalnodeid() IS 'Return the replication node id for this node, or NULL if not a replicated installation.';


CREATE FUNCTION public.gitrepository_denorm_access(gitrepository_id integer) RETURNS void
    LANGUAGE sql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
    UPDATE GitRepository
        SET access_policy = policies[1], access_grants = grants
        FROM
            build_access_cache(
                (SELECT id FROM accessartifact WHERE gitrepository = $1),
                (SELECT information_type FROM gitrepository WHERE id = $1))
            AS (policies integer[], grants integer[])
        WHERE id = $1;
$_$;


CREATE FUNCTION public.gitrepository_maintain_access_cache_trig() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM gitrepository_denorm_access(NEW.id);
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.is_blacklisted_name(text, integer) RETURNS boolean
    LANGUAGE sql STABLE STRICT SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
    SELECT COALESCE(name_blacklist_match($1, $2)::boolean, FALSE);
$_$;


COMMENT ON FUNCTION public.is_blacklisted_name(text, integer) IS 'Return TRUE if any regular expressions stored in the NameBlacklist table match the givenname, otherwise return FALSE.';


CREATE FUNCTION public.lp_mirror_account_ins() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    INSERT INTO lp_Account (id, openid_identifier)
    VALUES (NEW.id, NEW.openid_identifier);
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;


CREATE FUNCTION public.lp_mirror_account_upd() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    IF OLD.id <> NEW.id OR OLD.openid_identifier <> NEW.openid_identifier THEN
        UPDATE lp_Account
        SET id = NEW.id, openid_identifier = NEW.openid_identifier
        WHERE id = OLD.id;
    END IF;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;


CREATE FUNCTION public.lp_mirror_del() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    EXECUTE 'DELETE FROM lp_' || TG_TABLE_NAME || ' WHERE id=' || OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;


CREATE FUNCTION public.lp_mirror_openididentifier_del() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


CREATE FUNCTION public.lp_mirror_openididentifier_ins() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


CREATE FUNCTION public.lp_mirror_openididentifier_upd() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


CREATE FUNCTION public.lp_mirror_person_ins() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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
    VALUES (
        NEW.id, NEW.displayname, NEW.teamowner, NULL,
        NEW.name, NEW.language, NEW.fti, NEW.defaultmembershipperiod,
        NEW.defaultrenewalperiod, NEW.subscriptionpolicy,
        NEW.merged, NEW.datecreated, NULL, NEW.icon,
        NEW.mugshot, NEW.hide_email_addresses, NEW.creation_rationale,
        NEW.creation_comment, NEW.registrant, NEW.logo, NEW.renewal_policy,
        NEW.personal_standing, NEW.personal_standing_reason,
        NEW.mail_resumption_date, NEW.mailing_list_auto_subscribe_policy,
        NEW.mailing_list_receive_duplicates, NEW.visibility,
        NEW.verbose_bugnotifications, NEW.account);
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;


CREATE FUNCTION public.lp_mirror_person_upd() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    UPDATE lp_Person
    SET id = NEW.id,
        displayname = NEW.displayname,
        teamowner = NEW.teamowner,
        teamdescription = NULL,
        name = NEW.name,
        language = NEW.language,
        fti = NEW.fti,
        defaultmembershipperiod = NEW.defaultmembershipperiod,
        defaultrenewalperiod = NEW.defaultrenewalperiod,
        subscriptionpolicy = NEW.subscriptionpolicy,
        merged = NEW.merged,
        datecreated = NEW.datecreated,
        homepage_content = NULL,
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


CREATE FUNCTION public.lp_mirror_personlocation_ins() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    INSERT INTO lp_PersonLocation SELECT NEW.*;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;


CREATE FUNCTION public.lp_mirror_personlocation_upd() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


CREATE FUNCTION public.lp_mirror_teamparticipation_ins() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    INSERT INTO lp_TeamParticipation SELECT NEW.*;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;


CREATE FUNCTION public.lp_mirror_teamparticipation_upd() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    UPDATE lp_TeamParticipation
    SET id = NEW.id,
        team = NEW.team,
        person = NEW.person
    WHERE id = OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;


CREATE FUNCTION public.message_copy_owner_to_bugmessage() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.message_copy_owner_to_bugmessage() IS 'Copies the message owner into bugmessage when message changes.';


CREATE FUNCTION public.message_copy_owner_to_questionmessage() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.message_copy_owner_to_questionmessage() IS 'Copies the message owner into questionmessage when message changes.';


CREATE FUNCTION public.milestone_sort_key(dateexpected timestamp without time zone, name text) RETURNS text
    LANGUAGE plpythonu IMMUTABLE
    AS $$
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
$$;


COMMENT ON FUNCTION public.milestone_sort_key(dateexpected timestamp without time zone, name text) IS 'Sort by the Milestone dateexpected and name. If the dateexpected is NULL, then it is converted to a date far in the future, so it will be sorted as a milestone in the future.';


CREATE FUNCTION public.mv_branch_distribution_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.mv_branch_distribution_update() IS 'Maintain Branch name cache when Distribution is modified.';


CREATE FUNCTION public.mv_branch_distroseries_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.mv_branch_distroseries_update() IS 'Maintain Branch name cache when Distroseries is modified.';


CREATE FUNCTION public.mv_branch_person_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.mv_branch_person_update() IS 'Maintain Branch name cache when Person is modified.';


CREATE FUNCTION public.mv_branch_product_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.mv_branch_product_update() IS 'Maintain Branch name cache when Product is modified.';


CREATE FUNCTION public.mv_pillarname_distribution() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.mv_pillarname_distribution() IS 'Trigger maintaining the PillarName table';


CREATE FUNCTION public.mv_pillarname_product() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.mv_pillarname_product() IS 'Trigger maintaining the PillarName table';


CREATE FUNCTION public.mv_pillarname_project() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.mv_pillarname_project() IS 'Trigger maintaining the PillarName table';


CREATE FUNCTION public.mv_pofiletranslator_translationmessage() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    -- Update any existing entries.
    UPDATE POFileTranslator
    SET date_last_touched = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
    FROM POFile, TranslationTemplateItem
    WHERE person = NEW.submitter AND
        TranslationTemplateItem.potmsgset = NEW.potmsgset AND
        TranslationTemplateItem.potemplate = POFile.potemplate AND
        POFile.language = NEW.language AND
        POFileTranslator.pofile = POFile.id;

    -- Insert any missing entries.
    INSERT INTO POFileTranslator (person, pofile)
    SELECT DISTINCT NEW.submitter, POFile.id
    FROM TranslationTemplateItem
    JOIN POFile ON
        POFile.language = NEW.language AND
        POFile.potemplate = TranslationTemplateItem.potemplate
    WHERE
        TranslationTemplateItem.potmsgset = NEW.potmsgset AND
        NOT EXISTS (
            SELECT *
            FROM POFileTranslator
            WHERE person = NEW.submitter AND pofile = POFile.id
        );
    RETURN NULL;
END;
$$;


COMMENT ON FUNCTION public.mv_pofiletranslator_translationmessage() IS 'Trigger maintaining the POFileTranslator table';


CREATE FUNCTION public.mv_validpersonorteamcache_emailaddress() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $_$
    # This trigger function keeps the ValidPersonOrTeamCache materialized
    # view in sync when updates are made to the EmailAddress table.
    # Note that if the corresponding person is a team, changes to this table
    # have no effect.
    PREF = 4 # Constant indicating preferred email address

    if not SD.has_key("delete_plan"):
        param_types = ["int4"]

        SD["is_team"] = plpy.prepare("""
            SELECT teamowner IS NOT NULL AS is_team FROM Person WHERE id = $1
            """, param_types)

        SD["delete_plan"] = plpy.prepare("""
            DELETE FROM ValidPersonOrTeamCache WHERE id = $1
            """, param_types)

        SD["insert_plan"] = plpy.prepare("""
            INSERT INTO ValidPersonOrTeamCache (id) VALUES ($1)
            """, param_types)

        SD["maybe_insert_plan"] = plpy.prepare("""
            INSERT INTO ValidPersonOrTeamCache (id)
            SELECT Person.id
            FROM Person
                JOIN EmailAddress ON Person.id = EmailAddress.person
                LEFT OUTER JOIN ValidPersonOrTeamCache
                    ON Person.id = ValidPersonOrTeamCache.id
            WHERE Person.id = $1
                AND ValidPersonOrTeamCache.id IS NULL
                AND status = %(PREF)d
                AND merged IS NULL
                -- AND password IS NOT NULL
            """ % vars(), param_types)

    def is_team(person_id):
        """Return true if person_id corresponds to a team"""
        if person_id is None:
            return False
        return plpy.execute(SD["is_team"], [person_id], 1)[0]["is_team"]

    class NoneDict:
        def __getitem__(self, key):
            return None

    old = TD["old"] or NoneDict()
    new = TD["new"] or NoneDict()

    #plpy.info("old.id     == %s" % old["id"])
    #plpy.info("old.person == %s" % old["person"])
    #plpy.info("old.status == %s" % old["status"])
    #plpy.info("new.id     == %s" % new["id"])
    #plpy.info("new.person == %s" % new["person"])
    #plpy.info("new.status == %s" % new["status"])

    # Short circuit if neither person nor status has changed
    if old["person"] == new["person"] and old["status"] == new["status"]:
        return

    # Short circuit if we are not mucking around with preferred email
    # addresses
    if old["status"] != PREF and new["status"] != PREF:
        return

    # Note that we have a constraint ensuring that there is only one
    # status == PREF email address per person at any point in time.
    # This simplifies our logic, as we know that if old.status == PREF,
    # old.person does not have any other preferred email addresses.
    # Also if new.status == PREF, we know new.person previously did not
    # have a preferred email address.

    if old["person"] != new["person"]:
        if old["status"] == PREF and not is_team(old["person"]):
            # old.person is no longer valid, unless they are a team
            plpy.execute(SD["delete_plan"], [old["person"]])
        if new["status"] == PREF and not is_team(new["person"]):
            # new["person"] is now valid, or unchanged if they are a team
            plpy.execute(SD["insert_plan"], [new["person"]])

    elif old["status"] == PREF and not is_team(old["person"]):
        # No longer valid, or unchanged if they are a team
        plpy.execute(SD["delete_plan"], [old["person"]])

    elif new["status"] == PREF and not is_team(new["person"]):
        # May now be valid, or unchanged if they are a team.
        plpy.execute(SD["maybe_insert_plan"], [new["person"]])
$_$;


COMMENT ON FUNCTION public.mv_validpersonorteamcache_emailaddress() IS 'A trigger for maintaining the ValidPersonOrTeamCache eager materialized view when changes are made to the EmailAddress table';


CREATE FUNCTION public.mv_validpersonorteamcache_person() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $_$
    # This trigger function could be simplified by simply issuing
    # one DELETE followed by one INSERT statement. However, we want to minimize
    # expensive writes so we use this more complex logic.
    PREF = 4 # Constant indicating preferred email address

    if not SD.has_key("delete_plan"):
        param_types = ["int4"]

        SD["delete_plan"] = plpy.prepare("""
            DELETE FROM ValidPersonOrTeamCache WHERE id = $1
            """, param_types)

        SD["maybe_insert_plan"] = plpy.prepare("""
            INSERT INTO ValidPersonOrTeamCache (id)
            SELECT Person.id
            FROM Person
                LEFT OUTER JOIN EmailAddress
                    ON Person.id = EmailAddress.person AND status = %(PREF)d
                LEFT OUTER JOIN ValidPersonOrTeamCache
                    ON Person.id = ValidPersonOrTeamCache.id
            WHERE Person.id = $1
                AND ValidPersonOrTeamCache.id IS NULL
                AND merged IS NULL
                AND (teamowner IS NOT NULL OR EmailAddress.id IS NOT NULL)
            """ % vars(), param_types)

    new = TD["new"]
    old = TD["old"]

    # We should always have new, as this is not a DELETE trigger
    assert new is not None, 'New is None'

    person_id = new["id"]
    query_params = [person_id] # All the same

    # Short circuit if this is a new person (not team), as it cannot
    # be valid until a status == 4 EmailAddress entry has been created
    # (unless it is a team, in which case it is valid on creation)
    if old is None:
        if new["teamowner"] is not None:
            plpy.execute(SD["maybe_insert_plan"], query_params)
        return

    # Short circuit if there are no relevant changes
    if (new["teamowner"] == old["teamowner"]
        and new["merged"] == old["merged"]):
        return

    # This function is only dealing with updates to the Person table.
    # This means we do not have to worry about EmailAddress changes here

    if (new["merged"] is not None or new["teamowner"] is None):
        plpy.execute(SD["delete_plan"], query_params)
    else:
        plpy.execute(SD["maybe_insert_plan"], query_params)
$_$;


COMMENT ON FUNCTION public.mv_validpersonorteamcache_person() IS 'A trigger for maintaining the ValidPersonOrTeamCache eager materialized view when changes are made to the Person table';


CREATE FUNCTION public.name_blacklist_match(text, integer) RETURNS integer
    LANGUAGE plpythonu STABLE STRICT SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
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
$_$;


COMMENT ON FUNCTION public.name_blacklist_match(text, integer) IS 'Return the id of the row in the NameBlacklist table that matches the given name, or NULL if no regexps in the NameBlacklist table match.';


CREATE FUNCTION public.null_count(p_values anyarray) RETURNS integer
    LANGUAGE plpgsql IMMUTABLE STRICT
    AS $$
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


COMMENT ON FUNCTION public.null_count(p_values anyarray) IS 'Return the number of NULLs in the first row of the given array.';


CREATE FUNCTION public.packageset_deleted_trig() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.packageset_deleted_trig() IS 'Remove any DAG edges leading to/from the deleted package set.';


CREATE FUNCTION public.packageset_inserted_trig() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- A new package set was inserted; make it a descendent of itself in
    -- the flattened package set inclusion table in order to facilitate
    -- querying.
    INSERT INTO flatpackagesetinclusion(parent, child)
      VALUES (NEW.id, NEW.id);
    RETURN NULL;
END;
$$;


COMMENT ON FUNCTION public.packageset_inserted_trig() IS 'Insert self-referencing DAG edge when a new package set is inserted.';


CREATE FUNCTION public.packagesetinclusion_deleted_trig() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.packagesetinclusion_deleted_trig() IS 'Maintain the transitive closure in the DAG when an edge leading to/from a package set is deleted.';


CREATE FUNCTION public.packagesetinclusion_inserted_trig() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.packagesetinclusion_inserted_trig() IS 'Maintain the transitive closure in the DAG for a newly inserted edge leading to/from a package set.';


CREATE FUNCTION public.person_sort_key(displayname text, name text) RETURNS text
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
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


COMMENT ON FUNCTION public.person_sort_key(displayname text, name text) IS 'Return a string suitable for sorting people on, generated by stripping noise out of displayname and concatenating name';


CREATE FUNCTION public.plpgsql_call_handler() RETURNS language_handler
    LANGUAGE c
    AS '$libdir/plpgsql', 'plpgsql_call_handler';


CREATE FUNCTION public.questionmessage_copy_owner_from_message() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.questionmessage_copy_owner_from_message() IS 'Copies the message owner into QuestionMessage when QuestionMessage changes.';


CREATE FUNCTION public.replication_lag() RETURNS interval
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.replication_lag() IS 'Returns the worst lag time in our cluster, or NULL if not a replicated installation. Only returns meaningful results on the lpmain replication set master.';


CREATE FUNCTION public.replication_lag(node_id integer) RETURNS interval
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.replication_lag(node_id integer) IS 'Returns the lag time of the lpmain replication set to the given node, or NULL if not a replicated installation. The node id parameter can be obtained by calling getlocalnodeid() on the relevant database. This function only returns meaningful results on the lpmain replication set master.';


CREATE FUNCTION public.sane_version(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $_$
    import re
    if re.search("""^(?ix)
        [0-9a-z]
        ( [0-9a-z] | [0-9a-z.-]*[0-9a-z] )*
        $""", args[0]):
        return 1
    return 0
$_$;


COMMENT ON FUNCTION public.sane_version(text) IS 'A sane version number for use by ProductRelease and DistroRelease. We may make it less strict if required, but it would be nice if we can enforce simple version strings because we use them in URLs';


CREATE FUNCTION public.set_bug_date_last_message() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.set_bug_date_last_message() IS 'AFTER INSERT trigger on BugMessage maintaining the Bug.date_last_message column';


CREATE FUNCTION public.set_bug_message_count() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.set_bug_message_count() IS 'AFTER UPDATE trigger on BugAffectsPerson maintaining the Bug.users_affected_count column';


CREATE FUNCTION public.set_bug_number_of_duplicates() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.set_bug_number_of_duplicates() IS 'AFTER UPDATE trigger on Bug maintaining the Bug.number_of_duplicates column';


CREATE FUNCTION public.set_bug_users_affected_count() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


CREATE FUNCTION public.set_bugtask_date_milestone_set() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


COMMENT ON FUNCTION public.set_bugtask_date_milestone_set() IS 'Update BugTask.date_milestone_set when BugTask.milestone is changed.';


CREATE FUNCTION public.set_date_status_set() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF OLD.status <> NEW.status THEN
        NEW.date_status_set = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
    END IF;
    RETURN NEW;
END;
$$;


COMMENT ON FUNCTION public.set_date_status_set() IS 'BEFORE UPDATE trigger on Account that maintains the Account.date_status_set column.';


CREATE FUNCTION public.sha1(text) RETURNS character
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
    import hashlib
    return hashlib.sha1(args[0]).hexdigest()
$$;


COMMENT ON FUNCTION public.sha1(text) IS 'Return the SHA1 one way cryptographic hash as a string of 40 hex digits';


CREATE FUNCTION public.specification_denorm_access(spec_id integer) RETURNS void
    LANGUAGE sql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
    UPDATE specification
        SET access_policy = policies[1], access_grants = grants
        FROM
            build_access_cache(
                (SELECT id FROM accessartifact WHERE specification = $1),
                (SELECT information_type FROM specification WHERE id = $1))
            AS (policies integer[], grants integer[])
        WHERE id = $1;
$_$;


CREATE FUNCTION public.specification_maintain_access_cache_trig() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM specification_denorm_access(NEW.id);
    RETURN NULL;
END;
$$;


CREATE FUNCTION public.summarise_bug(bug integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM bugsummary_journal_bug(bug_row(bug), 1);
END;
$$;


CREATE FUNCTION public.ulower(text) RETURNS text
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
    return args[0].decode('utf8').lower().encode('utf8')
$$;


COMMENT ON FUNCTION public.ulower(text) IS 'Return the lower case version of a UTF-8 encoded string.';


CREATE FUNCTION public.unsummarise_bug(bug integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM bugsummary_journal_bug(bug_row(bug), -1);
END;
$$;


CREATE FUNCTION public.update_branch_name_cache() RETURNS trigger
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


COMMENT ON FUNCTION public.update_branch_name_cache() IS 'Maintain the cached name columns in Branch.';


CREATE FUNCTION public.update_database_disk_utilization() RETURNS void
    LANGUAGE sql SECURITY DEFINER
    SET search_path TO 'public'
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


CREATE FUNCTION public.update_database_stats() RETURNS void
    LANGUAGE plpythonu SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
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
$_$;


COMMENT ON FUNCTION public.update_database_stats() IS 'Copies rows from pg_stat_user_tables into DatabaseTableStats. We use a stored procedure because it is problematic for us to grant permissions on objects in the pg_catalog schema.';


CREATE FUNCTION public.update_replication_lag_cache() RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
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


COMMENT ON FUNCTION public.update_replication_lag_cache() IS 'Updates the DatabaseReplicationLag materialized view.';


CREATE FUNCTION public.valid_absolute_url(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
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


COMMENT ON FUNCTION public.valid_absolute_url(text) IS 'Ensure the given test is a valid absolute URL, containing both protocol and network location';


CREATE FUNCTION public.valid_branch_name(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
    import re
    name = args[0]
    pat = r"^(?i)[a-z0-9][a-z0-9+\.\-@_]*\Z"
    if re.match(pat, name):
        return 1
    return 0
$$;


COMMENT ON FUNCTION public.valid_branch_name(text) IS 'validate a branch name.

    As per valid_name, except we allow uppercase and @';


CREATE FUNCTION public.valid_cve(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $_$
    import re
    name = args[0]
    pat = r"^(19|20)\d{2}-\d{4,}$"
    if re.match(pat, name):
        return 1
    return 0
$_$;


COMMENT ON FUNCTION public.valid_cve(text) IS 'validate a common vulnerability number as defined on www.cve.mitre.org, minus the CAN- or CVE- prefix.';


CREATE FUNCTION public.valid_debian_version(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $_$
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
$_$;


COMMENT ON FUNCTION public.valid_debian_version(text) IS 'validate a version number as per Debian Policy';


CREATE FUNCTION public.valid_fingerprint(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
    import re
    if re.match(r"[\dA-F]{40}", args[0]) is not None:
        return 1
    else:
        return 0
$$;


COMMENT ON FUNCTION public.valid_fingerprint(text) IS 'Returns true if passed a valid GPG fingerprint. Valid GPG fingerprints are a 40 character long hexadecimal number in uppercase.';


CREATE FUNCTION public.valid_git_repository_name(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
    import re
    name = args[0]
    pat = r"^(?i)[a-z0-9][a-z0-9+\.\-@_]*\Z"
    if not name.endswith(".git") and re.match(pat, name):
        return 1
    return 0
$$;


COMMENT ON FUNCTION public.valid_git_repository_name(text) IS 'validate a Git repository name.

    As per valid_branch_name, except we disallow names ending in ".git".';


CREATE FUNCTION public.valid_keyid(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
    import re
    if re.match(r"[\dA-F]{8}", args[0]) is not None:
        return 1
    else:
        return 0
$$;


COMMENT ON FUNCTION public.valid_keyid(text) IS 'Returns true if passed a valid GPG keyid. Valid GPG keyids are an 8 character long hexadecimal number in uppercase (in reality, they are 16 characters long but we are using the ''common'' definition.';


CREATE FUNCTION public.valid_regexp(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
    import re
    try:
        re.compile(args[0])
    except:
        return False
    else:
        return True
$$;


COMMENT ON FUNCTION public.valid_regexp(text) IS 'Returns true if the input can be compiled as a regular expression.';


CREATE FUNCTION public.version_sort_key(version text) RETURNS text
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $$
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


COMMENT ON FUNCTION public.version_sort_key(version text) IS 'Sort a field as version numbers that do not necessarily conform to debian package versions (For example, when "2-2" should be considered greater than "1:1"). debversion_sort_key() should be used for debian versions. Numbers will be sorted after letters unlike typical ASCII, so that a descending sort will put the latest version number that starts with a number instead of a letter will be at the top. E.g. ascending is [a, z, 1, 9] and descending is [9, 1, z, a].';


CREATE FUNCTION public.you_are_your_own_member() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        INSERT INTO TeamParticipation (person, team)
            VALUES (NEW.id, NEW.id);
        RETURN NULL;
    END;
$$;


COMMENT ON FUNCTION public.you_are_your_own_member() IS 'Trigger function to ensure that every row added to the Person table gets a corresponding row in the TeamParticipation table, as per the TeamParticipationUsage page on the Launchpad wiki';


CREATE OPERATOR public.> (
    PROCEDURE = public.debversion_gt,
    LEFTARG = public.debversion,
    RIGHTARG = public.debversion,
    COMMUTATOR = OPERATOR(public.<),
    NEGATOR = OPERATOR(public.>=)
);


COMMENT ON OPERATOR public.> (public.debversion, public.debversion) IS 'debversion greater-than';


CREATE AGGREGATE public.max(public.debversion) (
    SFUNC = public.debversion_larger,
    STYPE = public.debversion,
    SORTOP = OPERATOR(public.>)
);


CREATE OPERATOR public.< (
    PROCEDURE = public.debversion_lt,
    LEFTARG = public.debversion,
    RIGHTARG = public.debversion,
    COMMUTATOR = OPERATOR(public.>),
    NEGATOR = OPERATOR(public.>=)
);


COMMENT ON OPERATOR public.< (public.debversion, public.debversion) IS 'debversion less-than';


CREATE AGGREGATE public.min(public.debversion) (
    SFUNC = public.debversion_smaller,
    STYPE = public.debversion,
    SORTOP = OPERATOR(public.<)
);


CREATE OPERATOR public.<= (
    PROCEDURE = public.debversion_le,
    LEFTARG = public.debversion,
    RIGHTARG = public.debversion,
    COMMUTATOR = OPERATOR(public.>=),
    NEGATOR = OPERATOR(public.>)
);


COMMENT ON OPERATOR public.<= (public.debversion, public.debversion) IS 'debversion less-than-or-equal';


CREATE OPERATOR public.<> (
    PROCEDURE = public.debversion_ne,
    LEFTARG = public.debversion,
    RIGHTARG = public.debversion,
    COMMUTATOR = OPERATOR(public.<>),
    NEGATOR = OPERATOR(public.=)
);


COMMENT ON OPERATOR public.<> (public.debversion, public.debversion) IS 'debversion not equal';


CREATE OPERATOR public.= (
    PROCEDURE = public.debversion_eq,
    LEFTARG = public.debversion,
    RIGHTARG = public.debversion,
    COMMUTATOR = OPERATOR(public.=),
    NEGATOR = OPERATOR(public.<>)
);


COMMENT ON OPERATOR public.= (public.debversion, public.debversion) IS 'debversion equal';


CREATE OPERATOR public.>= (
    PROCEDURE = public.debversion_ge,
    LEFTARG = public.debversion,
    RIGHTARG = public.debversion,
    COMMUTATOR = OPERATOR(public.<=),
    NEGATOR = OPERATOR(public.<)
);


COMMENT ON OPERATOR public.>= (public.debversion, public.debversion) IS 'debversion greater-than-or-equal';


CREATE OPERATOR FAMILY public.debversion_ops USING btree;


CREATE OPERATOR CLASS public.debversion_ops
    DEFAULT FOR TYPE public.debversion USING btree FAMILY public.debversion_ops AS
    OPERATOR 1 public.<(public.debversion,public.debversion) ,
    OPERATOR 2 public.<=(public.debversion,public.debversion) ,
    OPERATOR 3 public.=(public.debversion,public.debversion) ,
    OPERATOR 4 public.>=(public.debversion,public.debversion) ,
    OPERATOR 5 public.>(public.debversion,public.debversion) ,
    FUNCTION 1 (public.debversion, public.debversion) public.debversion_cmp(public.debversion,public.debversion);


CREATE OPERATOR FAMILY public.debversion_ops USING hash;


CREATE OPERATOR CLASS public.debversion_ops
    DEFAULT FOR TYPE public.debversion USING hash FAMILY public.debversion_ops AS
    OPERATOR 1 public.=(public.debversion,public.debversion) ,
    FUNCTION 1 (public.debversion, public.debversion) public.debversion_hash(public.debversion);


CREATE CAST (character AS public.debversion) WITH FUNCTION public.debversion(character);


CREATE CAST (public.debversion AS character) WITHOUT FUNCTION AS ASSIGNMENT;


CREATE CAST (public.debversion AS text) WITHOUT FUNCTION AS IMPLICIT;


CREATE CAST (public.debversion AS character varying) WITHOUT FUNCTION AS IMPLICIT;


CREATE CAST (text AS public.debversion) WITHOUT FUNCTION AS ASSIGNMENT;


CREATE CAST (character varying AS public.debversion) WITHOUT FUNCTION AS ASSIGNMENT;


CREATE TEXT SEARCH CONFIGURATION public."default" (
    PARSER = pg_catalog."default" );

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR asciiword WITH english_stem;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR word WITH english_stem;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR numword WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR email WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR url WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR host WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR sfloat WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR version WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR hword_numpart WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR hword_part WITH english_stem;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR hword_asciipart WITH english_stem;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR numhword WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR asciihword WITH english_stem;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR hword WITH english_stem;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR url_path WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR file WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR "float" WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR "int" WITH simple;

ALTER TEXT SEARCH CONFIGURATION public."default"
    ADD MAPPING FOR uint WITH simple;


CREATE TABLE public.accessartifact (
    id integer NOT NULL,
    bug integer,
    branch integer,
    specification integer,
    gitrepository integer,
    CONSTRAINT has_artifact CHECK ((public.null_count(ARRAY[bug, branch, gitrepository, specification]) = 3))
);


COMMENT ON TABLE public.accessartifact IS 'An artifact that an access grant can apply to. Additional private artifacts should be handled by adding new columns here, rather than new tables or columns on AccessArtifactGrant.';


COMMENT ON COLUMN public.accessartifact.bug IS 'The bug that this abstract artifact represents.';


COMMENT ON COLUMN public.accessartifact.branch IS 'The branch that this abstract artifact represents.';


CREATE SEQUENCE public.accessartifact_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.accessartifact_id_seq OWNED BY public.accessartifact.id;


CREATE TABLE public.accessartifactgrant (
    artifact integer NOT NULL,
    grantee integer NOT NULL,
    grantor integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.accessartifactgrant IS 'A grant for a person to access an artifact.';


COMMENT ON COLUMN public.accessartifactgrant.artifact IS 'The artifact on which access is granted.';


COMMENT ON COLUMN public.accessartifactgrant.grantee IS 'The person to whom access is granted.';


COMMENT ON COLUMN public.accessartifactgrant.grantor IS 'The person who granted the access.';


COMMENT ON COLUMN public.accessartifactgrant.date_created IS 'The date the access was granted.';


CREATE TABLE public.accesspolicy (
    id integer NOT NULL,
    product integer,
    distribution integer,
    type integer,
    person integer,
    CONSTRAINT has_target CHECK (((((type IS NOT NULL) AND ((product IS NULL) <> (distribution IS NULL))) AND (person IS NULL)) OR ((((type IS NULL) AND (person IS NOT NULL)) AND (product IS NULL)) AND (distribution IS NULL))))
);


COMMENT ON TABLE public.accesspolicy IS 'An access policy used to manage a project or distribution''s artifacts.';


COMMENT ON COLUMN public.accesspolicy.product IS 'The product that this policy is used on.';


COMMENT ON COLUMN public.accesspolicy.distribution IS 'The distribution that this policy is used on.';


COMMENT ON COLUMN public.accesspolicy.type IS 'The type of policy (an enum value). Private, Security, etc.';


COMMENT ON COLUMN public.accesspolicy.person IS 'The private team that this policy is used on.';


CREATE SEQUENCE public.accesspolicy_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.accesspolicy_id_seq OWNED BY public.accesspolicy.id;


CREATE TABLE public.accesspolicyartifact (
    artifact integer NOT NULL,
    policy integer NOT NULL
);


COMMENT ON TABLE public.accesspolicyartifact IS 'An association between an artifact and a policy. A grant for any related policy grants access to the artifact.';


COMMENT ON COLUMN public.accesspolicyartifact.artifact IS 'The artifact associated with this policy.';


COMMENT ON COLUMN public.accesspolicyartifact.policy IS 'The policy associated with this artifact.';


CREATE TABLE public.accesspolicygrant (
    policy integer NOT NULL,
    grantee integer NOT NULL,
    grantor integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.accesspolicygrant IS 'A grant for a person to access a policy''s artifacts.';


COMMENT ON COLUMN public.accesspolicygrant.policy IS 'The policy on which access is granted.';


COMMENT ON COLUMN public.accesspolicygrant.grantee IS 'The person to whom access is granted.';


COMMENT ON COLUMN public.accesspolicygrant.grantor IS 'The person who granted the access.';


COMMENT ON COLUMN public.accesspolicygrant.date_created IS 'The date the access was granted.';


CREATE TABLE public.accesspolicygrantflat (
    id integer NOT NULL,
    policy integer NOT NULL,
    artifact integer,
    grantee integer NOT NULL
);


COMMENT ON TABLE public.accesspolicygrantflat IS 'A fact table for access queries. AccessPolicyGrants are included verbatim, but AccessArtifactGrants are included with their artifacts'' corresponding policies.';


COMMENT ON COLUMN public.accesspolicygrantflat.policy IS 'The policy on which access is granted.';


COMMENT ON COLUMN public.accesspolicygrantflat.artifact IS 'The artifact on which access is granted. If null, the grant is for the whole policy';


COMMENT ON COLUMN public.accesspolicygrantflat.grantee IS 'The person to whom access is granted.';


CREATE SEQUENCE public.accesspolicygrantflat_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.accesspolicygrantflat_id_seq OWNED BY public.accesspolicygrantflat.id;


CREATE TABLE public.account (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    creation_rationale integer NOT NULL,
    status integer NOT NULL,
    date_status_set timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    displayname text NOT NULL,
    status_comment text
);


COMMENT ON TABLE public.account IS 'An account that may be used for authenticating to Canonical or other systems.';


COMMENT ON COLUMN public.account.status IS 'The status of the account.';


COMMENT ON COLUMN public.account.date_status_set IS 'When the status was last changed.';


COMMENT ON COLUMN public.account.displayname IS 'Name to display when rendering information about this account.';


COMMENT ON COLUMN public.account.status_comment IS 'The comment on the status of the account.';


CREATE SEQUENCE public.account_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.account_id_seq OWNED BY public.account.id;


CREATE TABLE public.announcement (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_announced timestamp without time zone,
    registrant integer NOT NULL,
    product integer,
    distribution integer,
    project integer,
    title text NOT NULL,
    summary text,
    url text,
    active boolean DEFAULT true NOT NULL,
    date_updated timestamp without time zone,
    CONSTRAINT has_target CHECK ((((product IS NOT NULL) OR (project IS NOT NULL)) OR (distribution IS NOT NULL))),
    CONSTRAINT valid_url CHECK (public.valid_absolute_url(url))
);


COMMENT ON TABLE public.announcement IS 'A project announcement. This is a single item of news or information that the project is communicating. Announcements can be attached to a Project, a Product or a Distribution.';


COMMENT ON COLUMN public.announcement.date_announced IS 'The date at which an announcement will become public, if it is active. If this is not set then the announcement will not become public until someone consciously publishes it (which sets this date).';


COMMENT ON COLUMN public.announcement.url IS 'A web location for the announcement itself.';


COMMENT ON COLUMN public.announcement.active IS 'Whether or not the announcement is public. This is TRUE by default, but can be set to FALSE if the project "retracts" the announcement.';


CREATE SEQUENCE public.announcement_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.announcement_id_seq OWNED BY public.announcement.id;


CREATE TABLE public.answercontact (
    id integer NOT NULL,
    product integer,
    distribution integer,
    sourcepackagename integer,
    person integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT valid_target CHECK ((((product IS NULL) <> (distribution IS NULL)) AND ((product IS NULL) OR (sourcepackagename IS NULL))))
);


COMMENT ON TABLE public.answercontact IS 'Defines the answer contact for a given question target. The answer contact will be automatically notified about changes to any questions filed on the question target.';


COMMENT ON COLUMN public.answercontact.product IS 'The product that the answer contact supports.';


COMMENT ON COLUMN public.answercontact.distribution IS 'The distribution that the answer contact supports.';


COMMENT ON COLUMN public.answercontact.sourcepackagename IS 'The sourcepackagename that the answer contact supports.';


COMMENT ON COLUMN public.answercontact.person IS 'The person or team associated with the question target.';


COMMENT ON COLUMN public.answercontact.date_created IS 'The date the answer contact was submitted.';


CREATE SEQUENCE public.answercontact_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.answercontact_id_seq OWNED BY public.answercontact.id;


CREATE TABLE public.apportjob (
    id integer NOT NULL,
    job integer NOT NULL,
    blob integer NOT NULL,
    job_type integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.apportjob IS 'Contains references to jobs to be run against Apport BLOBs.';


COMMENT ON COLUMN public.apportjob.blob IS 'The TemporaryBlobStorage entry on which the job is to be run.';


COMMENT ON COLUMN public.apportjob.job_type IS 'The type of job (enumeration value). Allows us to query the database for a given subset of ApportJobs.';


COMMENT ON COLUMN public.apportjob.json_data IS 'A JSON struct containing data for the job.';


CREATE SEQUENCE public.apportjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.apportjob_id_seq OWNED BY public.apportjob.id;


CREATE TABLE public.archive (
    id integer NOT NULL,
    owner integer NOT NULL,
    description text,
    enabled boolean DEFAULT true NOT NULL,
    authorized_size integer,
    distribution integer NOT NULL,
    purpose integer NOT NULL,
    private boolean DEFAULT false NOT NULL,
    sources_cached integer,
    binaries_cached integer,
    package_description_cache text,
    fti public.ts2_tsvector,
    buildd_secret text,
    require_virtualized boolean DEFAULT true NOT NULL,
    name text DEFAULT 'default'::text NOT NULL,
    publish boolean DEFAULT true NOT NULL,
    date_updated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    total_count integer DEFAULT 0 NOT NULL,
    pending_count integer DEFAULT 0 NOT NULL,
    succeeded_count integer DEFAULT 0 NOT NULL,
    failed_count integer DEFAULT 0 NOT NULL,
    building_count integer DEFAULT 0 NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    signing_key integer,
    removed_binary_retention_days integer,
    num_old_versions_published integer,
    displayname text NOT NULL,
    relative_build_score integer DEFAULT 0 NOT NULL,
    external_dependencies text,
    status integer DEFAULT 0 NOT NULL,
    suppress_subscription_notifications boolean DEFAULT false NOT NULL,
    build_debug_symbols boolean DEFAULT false NOT NULL,
    publish_debug_symbols boolean DEFAULT false,
    permit_obsolete_series_uploads boolean DEFAULT false,
    signing_key_owner integer,
    signing_key_fingerprint text,
    dirty_suites text,
    CONSTRAINT valid_buildd_secret CHECK ((((private = true) AND (buildd_secret IS NOT NULL)) OR (private = false))),
    CONSTRAINT valid_name CHECK (public.valid_name(name)),
    CONSTRAINT valid_signing_key_fingerprint CHECK (((signing_key_fingerprint IS NULL) OR public.valid_fingerprint(signing_key_fingerprint)))
);


COMMENT ON TABLE public.archive IS 'A package archive. Commonly either a distribution''s main_archive or a ppa''s archive.';


COMMENT ON COLUMN public.archive.owner IS 'Identifies the PPA owner when it has one.';


COMMENT ON COLUMN public.archive.description IS 'Allow users to describe their PPAs content.';


COMMENT ON COLUMN public.archive.enabled IS 'Whether or not the PPA is enabled for accepting uploads.';


COMMENT ON COLUMN public.archive.authorized_size IS 'Size, in MiB, allowed for this PPA.';


COMMENT ON COLUMN public.archive.distribution IS 'The distribution that uses this archive.';


COMMENT ON COLUMN public.archive.purpose IS 'The purpose of this archive, e.g. COMMERCIAL.  See the ArchivePurpose DBSchema item.';


COMMENT ON COLUMN public.archive.private IS 'Whether or not the archive is private. This affects the global visibility of the archive.';


COMMENT ON COLUMN public.archive.sources_cached IS 'Number of sources already cached for this archive.';


COMMENT ON COLUMN public.archive.binaries_cached IS 'Number of binaries already cached for this archive.';


COMMENT ON COLUMN public.archive.package_description_cache IS 'Text blob containing all source and binary names and descriptions concatenated. Used to to build the tsearch indexes on this table.';


COMMENT ON COLUMN public.archive.require_virtualized IS 'Whether this archive has binaries that should be built on a virtual machine, e.g. PPAs';


COMMENT ON COLUMN public.archive.name IS 'The name of the archive.';


COMMENT ON COLUMN public.archive.publish IS 'Whether this archive should be published.';


COMMENT ON COLUMN public.archive.date_updated IS 'When were the rebuild statistics last updated?';


COMMENT ON COLUMN public.archive.total_count IS 'How many source packages are in the rebuild archive altogether?';


COMMENT ON COLUMN public.archive.pending_count IS 'How many packages still need building?';


COMMENT ON COLUMN public.archive.succeeded_count IS 'How many source packages were built sucessfully?';


COMMENT ON COLUMN public.archive.failed_count IS 'How many packages failed to build?';


COMMENT ON COLUMN public.archive.building_count IS 'How many packages are building at present?';


COMMENT ON COLUMN public.archive.signing_key IS 'The GpgKey used for signing this archive.';


COMMENT ON COLUMN public.archive.removed_binary_retention_days IS 'The number of days before superseded or deleted binary files are expired in the librarian, or zero for never.';


COMMENT ON COLUMN public.archive.num_old_versions_published IS 'The number of versions of a package to keep published before older versions are superseded.';


COMMENT ON COLUMN public.archive.displayname IS 'User defined displayname for this archive.';


COMMENT ON COLUMN public.archive.relative_build_score IS 'A delta to the build score that is applied to all builds in this archive.';


COMMENT ON COLUMN public.archive.external_dependencies IS 'Newline-separated list of repositories to be used to retrieve any external build dependencies when building packages in this archive, in the format: deb http[s]://[user:pass@]<host>[/path] %(series)s[-pocket] [components]  The series variable is replaced with the series name of the context build.  This column is specifically and only intended for OEM migration to Launchpad and should be re-examined in October 2010 to see if it is still relevant.';


COMMENT ON COLUMN public.archive.status IS 'The status of this archive, e.g. ACTIVE.  See the ArchiveState DBSchema item.';


COMMENT ON COLUMN public.archive.suppress_subscription_notifications IS 'Whether to suppress notifications about subscriptions.';


COMMENT ON COLUMN public.archive.build_debug_symbols IS 'Whether builds for this archive should create debug symbol packages.';


COMMENT ON COLUMN public.archive.dirty_suites IS 'A JSON-encoded list of suites in this archive that should be considered dirty on the next publisher run regardless of publications.';


CREATE SEQUENCE public.archive_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.archive_id_seq OWNED BY public.archive.id;


CREATE TABLE public.archivearch (
    id integer NOT NULL,
    archive integer NOT NULL,
    processor integer NOT NULL
);


COMMENT ON TABLE public.archivearch IS 'ArchiveArch: A table that allows a user to specify which architectures an archive requires or supports.';


COMMENT ON COLUMN public.archivearch.archive IS 'The archive for which an architecture is specified.';


COMMENT ON COLUMN public.archivearch.processor IS 'The architecture specified for the archive on hand.';


CREATE SEQUENCE public.archivearch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.archivearch_id_seq OWNED BY public.archivearch.id;


CREATE TABLE public.archiveauthtoken (
    id integer NOT NULL,
    archive integer NOT NULL,
    person integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_deactivated timestamp without time zone,
    token text NOT NULL,
    name text
);


COMMENT ON TABLE public.archiveauthtoken IS 'Authorisation tokens to use in .htaccess for published archives.';


COMMENT ON COLUMN public.archiveauthtoken.archive IS 'The archive to which this token refers.';


COMMENT ON COLUMN public.archiveauthtoken.person IS 'The person to which this token applies.';


COMMENT ON COLUMN public.archiveauthtoken.date_created IS 'The date and time this token was created.';


COMMENT ON COLUMN public.archiveauthtoken.date_deactivated IS 'The date and time this token was deactivated.';


COMMENT ON COLUMN public.archiveauthtoken.token IS 'The token text for this authorisation.';


COMMENT ON COLUMN public.archiveauthtoken.name IS 'The name for this named token.';


CREATE SEQUENCE public.archiveauthtoken_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.archiveauthtoken_id_seq OWNED BY public.archiveauthtoken.id;


CREATE TABLE public.archivedependency (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    archive integer NOT NULL,
    dependency integer NOT NULL,
    pocket integer NOT NULL,
    component integer,
    CONSTRAINT distinct_archives CHECK ((archive <> dependency))
);


COMMENT ON TABLE public.archivedependency IS 'This table maps a given archive to all other archives it should depend on.';


COMMENT ON COLUMN public.archivedependency.date_created IS 'Instant when the dependency was created.';


COMMENT ON COLUMN public.archivedependency.archive IS 'The archive where the dependency should be applied.';


COMMENT ON COLUMN public.archivedependency.dependency IS 'The archive to depend on.';


CREATE SEQUENCE public.archivedependency_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.archivedependency_id_seq OWNED BY public.archivedependency.id;


CREATE TABLE public.archivefile (
    id integer NOT NULL,
    archive integer NOT NULL,
    container text NOT NULL,
    path text NOT NULL,
    library_file integer NOT NULL,
    scheduled_deletion_date timestamp without time zone
);


COMMENT ON TABLE public.archivefile IS 'A file in an archive.';


COMMENT ON COLUMN public.archivefile.archive IS 'The archive containing the file.';


COMMENT ON COLUMN public.archivefile.container IS 'An identifier for the component that manages this file.';


COMMENT ON COLUMN public.archivefile.path IS 'The path to the file within the published archive.';


COMMENT ON COLUMN public.archivefile.library_file IS 'The file in the librarian.';


COMMENT ON COLUMN public.archivefile.scheduled_deletion_date IS 'The date when this file should stop being published.';


CREATE SEQUENCE public.archivefile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.archivefile_id_seq OWNED BY public.archivefile.id;


CREATE TABLE public.archivejob (
    id integer NOT NULL,
    job integer NOT NULL,
    archive integer NOT NULL,
    job_type integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.archivejob IS 'Contains references to jobs to be run against Archives.';


COMMENT ON COLUMN public.archivejob.archive IS 'The archive on which the job is to be run.';


COMMENT ON COLUMN public.archivejob.job_type IS 'The type of job (enumeration value). Allows us to query the database for a given subset of ArchiveJobs.';


COMMENT ON COLUMN public.archivejob.json_data IS 'A JSON struct containing data for the job.';


CREATE SEQUENCE public.archivejob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.archivejob_id_seq OWNED BY public.archivejob.id;


CREATE TABLE public.archivepermission (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    person integer NOT NULL,
    permission integer NOT NULL,
    archive integer NOT NULL,
    component integer,
    sourcepackagename integer,
    packageset integer,
    explicit boolean DEFAULT false NOT NULL,
    pocket integer,
    distroseries integer,
    CONSTRAINT one_target CHECK ((public.null_count(ARRAY[packageset, component, sourcepackagename, pocket]) = 3))
);


COMMENT ON TABLE public.archivepermission IS 'ArchivePermission: A record of who has permission to upload and approve uploads to an archive (and hence a distribution)';


COMMENT ON COLUMN public.archivepermission.date_created IS 'The date that this permission was created.';


COMMENT ON COLUMN public.archivepermission.person IS 'The person or team to whom the permission is being granted.';


COMMENT ON COLUMN public.archivepermission.permission IS 'The permission type being granted.';


COMMENT ON COLUMN public.archivepermission.archive IS 'The archive to which this permission applies.';


COMMENT ON COLUMN public.archivepermission.component IS 'The component to which this upload permission applies.';


COMMENT ON COLUMN public.archivepermission.sourcepackagename IS 'The source package name to which this permission applies.  This can be used to provide package-level permissions to single users.';


COMMENT ON COLUMN public.archivepermission.packageset IS 'The package set to which this permission applies.';


COMMENT ON COLUMN public.archivepermission.explicit IS 'This flag is set for package sets containing high-profile packages that must not break and/or require specialist skills for proper handling e.g. the kernel.';


COMMENT ON COLUMN public.archivepermission.pocket IS 'The pocket to which this permission applies.';


COMMENT ON COLUMN public.archivepermission.distroseries IS 'An optional distroseries to which this permission applies.';


CREATE SEQUENCE public.archivepermission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.archivepermission_id_seq OWNED BY public.archivepermission.id;


CREATE TABLE public.archivesubscriber (
    id integer NOT NULL,
    archive integer NOT NULL,
    registrant integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    subscriber integer NOT NULL,
    date_expires timestamp without time zone,
    status integer NOT NULL,
    description text,
    date_cancelled timestamp without time zone,
    cancelled_by integer
);


COMMENT ON TABLE public.archivesubscriber IS 'An authorised person or team subscription to an archive.';


COMMENT ON COLUMN public.archivesubscriber.archive IS 'The archive that the subscriber is authorised to see.';


COMMENT ON COLUMN public.archivesubscriber.registrant IS 'The person who authorised this subscriber.';


COMMENT ON COLUMN public.archivesubscriber.date_created IS 'The date and time this subscription was created.';


COMMENT ON COLUMN public.archivesubscriber.subscriber IS 'The person or team that this subscription refers to.';


COMMENT ON COLUMN public.archivesubscriber.date_expires IS 'The date and time this subscription will expire. If NULL, it does not expire.';


COMMENT ON COLUMN public.archivesubscriber.status IS 'The status of the subscription, e.g. PENDING, ACTIVE, CANCELLING, CANCELLED.';


COMMENT ON COLUMN public.archivesubscriber.description IS 'An optional note for the archive owner to describe the subscription.';


COMMENT ON COLUMN public.archivesubscriber.date_cancelled IS 'The date and time this subscription was revoked.';


COMMENT ON COLUMN public.archivesubscriber.cancelled_by IS 'The person who revoked this subscription.';


CREATE SEQUENCE public.archivesubscriber_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.archivesubscriber_id_seq OWNED BY public.archivesubscriber.id;


CREATE TABLE public.binarypackagename (
    id integer NOT NULL,
    name text NOT NULL,
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.binarypackagename IS 'BinaryPackageName: A soyuz binary package name.';


COMMENT ON COLUMN public.binarypackagename.name IS 'A lowercase name identifying one or more binarypackages';


CREATE TABLE public.sourcepackagename (
    id integer NOT NULL,
    name text NOT NULL,
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.sourcepackagename IS 'SourcePackageName: A soyuz source package name.';


COMMENT ON COLUMN public.sourcepackagename.name IS 'A lowercase name identifying one or more sourcepackages';


CREATE VIEW public.binaryandsourcepackagenameview AS
 SELECT binarypackagename.name
   FROM public.binarypackagename
UNION
 SELECT sourcepackagename.name
   FROM public.sourcepackagename;


CREATE TABLE public.binarypackagebuild (
    id integer NOT NULL,
    distro_arch_series integer NOT NULL,
    source_package_release integer NOT NULL,
    archive integer NOT NULL,
    pocket integer NOT NULL,
    processor integer,
    virtualized boolean,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_started timestamp without time zone,
    date_finished timestamp without time zone,
    date_first_dispatched timestamp without time zone,
    builder integer,
    status integer NOT NULL,
    log integer,
    upload_log integer,
    dependencies text,
    failure_count integer DEFAULT 0 NOT NULL,
    build_farm_job integer NOT NULL,
    distribution integer NOT NULL,
    distro_series integer NOT NULL,
    is_distro_archive boolean NOT NULL,
    source_package_name integer NOT NULL,
    arch_indep boolean NOT NULL,
    external_dependencies text,
    buildinfo integer
);


COMMENT ON TABLE public.binarypackagebuild IS 'BinaryPackageBuild: This table links a package build with a distroarchseries and sourcepackagerelease.';


COMMENT ON COLUMN public.binarypackagebuild.distro_arch_series IS 'Points the target DistroArchSeries for this build.';


COMMENT ON COLUMN public.binarypackagebuild.source_package_release IS 'SourcePackageRelease which originated this build.';


COMMENT ON COLUMN public.binarypackagebuild.external_dependencies IS 'Newline-separated list of repositories to be used to retrieve any external build dependencies when performing this build, in the format: "deb http[s]://[user:pass@]<host>[/path] series[-pocket] [components]".  This is intended for bootstrapping build-dependency loops.';


CREATE SEQUENCE public.binarypackagebuild_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.binarypackagebuild_id_seq OWNED BY public.binarypackagebuild.id;


CREATE TABLE public.binarypackagefile (
    binarypackagerelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval(('binarypackagefile_id_seq'::text)::regclass) NOT NULL
);


COMMENT ON TABLE public.binarypackagefile IS 'BinaryPackageFile: A soyuz <-> librarian link table. This table represents the ownership in the librarian of a file which represents a binary package';


COMMENT ON COLUMN public.binarypackagefile.binarypackagerelease IS 'The binary package which is represented by the file';


COMMENT ON COLUMN public.binarypackagefile.libraryfile IS 'The file in the librarian which represents the package';


COMMENT ON COLUMN public.binarypackagefile.filetype IS 'The "type" of the file. E.g. DEB, RPM';


CREATE SEQUENCE public.binarypackagefile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.binarypackagefile_id_seq OWNED BY public.binarypackagefile.id;


CREATE SEQUENCE public.binarypackagename_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.binarypackagename_id_seq OWNED BY public.binarypackagename.id;


CREATE TABLE public.binarypackagepublishinghistory (
    id integer NOT NULL,
    binarypackagerelease integer NOT NULL,
    distroarchseries integer NOT NULL,
    status integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    priority integer NOT NULL,
    datecreated timestamp without time zone NOT NULL,
    datepublished timestamp without time zone,
    datesuperseded timestamp without time zone,
    supersededby integer,
    datemadepending timestamp without time zone,
    scheduleddeletiondate timestamp without time zone,
    dateremoved timestamp without time zone,
    pocket integer DEFAULT 0 NOT NULL,
    archive integer NOT NULL,
    removed_by integer,
    removal_comment text,
    binarypackagename integer NOT NULL,
    phased_update_percentage smallint
);


COMMENT ON TABLE public.binarypackagepublishinghistory IS 'PackagePublishingHistory: The history of a BinaryPackagePublishing record. This table represents the lifetime of a publishing record from inception to deletion. Records are never removed from here and in time the publishing table may become a view onto this table. A column being NULL indicates there''s no data for that state transition. E.g. a package which is removed without being superseded won''t have datesuperseded or supersededby filled in.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.binarypackagerelease IS 'The binarypackage being published.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.distroarchseries IS 'The distroarchseries into which the binarypackage is being published.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.status IS 'The current status of the publishing.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.component IS 'The component into which the publishing takes place.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.section IS 'The section into which the publishing takes place.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.priority IS 'The priority at which the publishing takes place.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.datecreated IS 'The date/time on which the publishing record was created.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.datepublished IS 'The date/time on which the source was actually published into an archive.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.datesuperseded IS 'The date/time on which the source was superseded by a new source.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.supersededby IS 'The build which superseded this package. This seems odd but it is important because a new build may not actually build a given binarypackage and we need to supersede it appropriately';


COMMENT ON COLUMN public.binarypackagepublishinghistory.datemadepending IS 'The date/time on which this publishing record was made to be pending removal from the archive.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.scheduleddeletiondate IS 'The date/time at which the package is/was scheduled to be deleted.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.dateremoved IS 'The date/time at which the package was actually deleted.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.pocket IS 'The pocket into which this record is published. The RELEASE pocket (zero) provides behaviour as normal. Other pockets may append things to the distroseries name such as the UPDATES pocket (-updates) or the SECURITY pocket (-security).';


COMMENT ON COLUMN public.binarypackagepublishinghistory.archive IS 'Target archive for this publishing record.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.removed_by IS 'Person responsible for the removal.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.removal_comment IS 'Reason why the publication was removed.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.binarypackagename IS 'Reference to a BinaryPackageName.';


COMMENT ON COLUMN public.binarypackagepublishinghistory.phased_update_percentage IS 'Percentage of users for whom this package should be recommended. NULL indicates no phasing, i.e. publish the update for everyone.';


CREATE SEQUENCE public.binarypackagepublishinghistory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.binarypackagepublishinghistory_id_seq OWNED BY public.binarypackagepublishinghistory.id;


CREATE TABLE public.binarypackagerelease (
    id integer NOT NULL,
    binarypackagename integer NOT NULL,
    version public.debversion NOT NULL,
    summary text NOT NULL,
    description text NOT NULL,
    build integer NOT NULL,
    binpackageformat integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    priority integer NOT NULL,
    shlibdeps text,
    depends text,
    recommends text,
    suggests text,
    conflicts text,
    replaces text,
    provides text,
    essential boolean NOT NULL,
    installedsize integer,
    architecturespecific boolean NOT NULL,
    fti public.ts2_tsvector,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    pre_depends text,
    enhances text,
    breaks text,
    debug_package integer,
    user_defined_fields text,
    homepage text,
    CONSTRAINT valid_version CHECK (public.valid_debian_version((version)::text))
);


COMMENT ON TABLE public.binarypackagerelease IS 'BinaryPackageRelease: A soyuz binary package representation. This table stores the records for each binary package uploaded into the system. Each sourcepackagerelease may build various binarypackages on various architectures.';


COMMENT ON COLUMN public.binarypackagerelease.binarypackagename IS 'A reference to the name of the binary package';


COMMENT ON COLUMN public.binarypackagerelease.version IS 'The version of the binary package. E.g. "1.0-2"';


COMMENT ON COLUMN public.binarypackagerelease.summary IS 'A summary of the binary package. Commonly used on listings of binary packages';


COMMENT ON COLUMN public.binarypackagerelease.description IS 'A longer more detailed description of the binary package';


COMMENT ON COLUMN public.binarypackagerelease.build IS 'The build in which this binarypackage was produced';


COMMENT ON COLUMN public.binarypackagerelease.binpackageformat IS 'The binarypackage format. E.g. RPM, DEB etc';


COMMENT ON COLUMN public.binarypackagerelease.component IS 'The archive component that this binarypackage is in. E.g. main, universe etc';


COMMENT ON COLUMN public.binarypackagerelease.section IS 'The archive section that this binarypackage is in. E.g. devel, libdevel, editors';


COMMENT ON COLUMN public.binarypackagerelease.priority IS 'The priority that this package has. E.g. Base, Standard, Extra, Optional';


COMMENT ON COLUMN public.binarypackagerelease.shlibdeps IS 'The shared library dependencies of this binary package';


COMMENT ON COLUMN public.binarypackagerelease.depends IS 'The list of packages this binarypackage depends on';


COMMENT ON COLUMN public.binarypackagerelease.recommends IS 'The list of packages this binarypackage recommends. Recommended packages often enhance the behaviour of a package.';


COMMENT ON COLUMN public.binarypackagerelease.suggests IS 'The list of packages this binarypackage suggests.';


COMMENT ON COLUMN public.binarypackagerelease.conflicts IS 'The list of packages this binarypackage conflicts with.';


COMMENT ON COLUMN public.binarypackagerelease.replaces IS 'The list of packages this binarypackage replaces files in. Often this is used to provide an upgrade path between two binarypackages of different names';


COMMENT ON COLUMN public.binarypackagerelease.provides IS 'The list of virtual packages (or real packages under some circumstances) which this binarypackage provides.';


COMMENT ON COLUMN public.binarypackagerelease.essential IS 'Whether or not this binarypackage is essential to the smooth operation of a base system';


COMMENT ON COLUMN public.binarypackagerelease.installedsize IS 'What the installed size of the binarypackage is. This is represented as a number of kilobytes of storage.';


COMMENT ON COLUMN public.binarypackagerelease.architecturespecific IS 'This field indicates whether or not a binarypackage is architecture-specific. If it is not specific to any given architecture then it can automatically be included in all the distroarchseries which pertain.';


COMMENT ON COLUMN public.binarypackagerelease.pre_depends IS 'The list of packages this binary requires to be installed beforehand in apt/dpkg format, as it is in control file "Pre-Depends:" field.';


COMMENT ON COLUMN public.binarypackagerelease.enhances IS 'The list of packages pointed as "enhanced" after the installation of this package, as it is in control file "Enhances:" field.';


COMMENT ON COLUMN public.binarypackagerelease.breaks IS 'The list of packages which will be broken by the installtion of this package, as it is in the control file "Breaks:" field.';


COMMENT ON COLUMN public.binarypackagerelease.debug_package IS 'The corresponding binary package release containing debug symbols for this binary, if any.';


COMMENT ON COLUMN public.binarypackagerelease.user_defined_fields IS 'A JSON struct containing a sequence of key-value pairs with user defined fields in the control file.';


COMMENT ON COLUMN public.binarypackagerelease.homepage IS 'Upstream project homepage URL, not checked for validity.';


CREATE SEQUENCE public.binarypackagerelease_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.binarypackagerelease_id_seq OWNED BY public.binarypackagerelease.id;


CREATE TABLE public.binarypackagereleasedownloadcount (
    id integer NOT NULL,
    archive integer NOT NULL,
    binary_package_release integer NOT NULL,
    day date NOT NULL,
    country integer,
    count integer NOT NULL
);


CREATE SEQUENCE public.binarypackagereleasedownloadcount_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.binarypackagereleasedownloadcount_id_seq OWNED BY public.binarypackagereleasedownloadcount.id;


CREATE TABLE public.branch (
    id integer NOT NULL,
    title text,
    summary text,
    owner integer NOT NULL,
    product integer,
    name text NOT NULL,
    home_page text,
    url text,
    whiteboard text,
    lifecycle_status integer DEFAULT 1 NOT NULL,
    last_mirrored timestamp without time zone,
    last_mirror_attempt timestamp without time zone,
    mirror_failures integer DEFAULT 0 NOT NULL,
    mirror_status_message text,
    last_scanned timestamp without time zone,
    last_scanned_id text,
    last_mirrored_id text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    revision_count integer DEFAULT 0 NOT NULL,
    next_mirror_time timestamp without time zone,
    branch_type integer NOT NULL,
    reviewer integer,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    branch_format integer,
    repository_format integer,
    metadir_format integer,
    stacked_on integer,
    distroseries integer,
    sourcepackagename integer,
    owner_name text NOT NULL,
    target_suffix text,
    unique_name text,
    size_on_disk bigint,
    information_type integer NOT NULL,
    access_policy integer,
    access_grants integer[],
    CONSTRAINT branch_type_url_consistent CHECK (((((branch_type = 2) AND (url IS NOT NULL)) OR ((branch_type = ANY (ARRAY[1, 3])) AND (url IS NULL))) OR (branch_type = 4))),
    CONSTRAINT branch_url_no_trailing_slash CHECK ((url !~~ '%/'::text)),
    CONSTRAINT branch_url_not_supermirror CHECK ((url !~~ 'http://bazaar.launchpad.net/%'::text)),
    CONSTRAINT one_container CHECK ((((distroseries IS NULL) = (sourcepackagename IS NULL)) AND ((distroseries IS NULL) OR (product IS NULL)))),
    CONSTRAINT valid_home_page CHECK (public.valid_absolute_url(home_page)),
    CONSTRAINT valid_name CHECK (public.valid_branch_name(name)),
    CONSTRAINT valid_url CHECK (public.valid_absolute_url(url))
);


COMMENT ON TABLE public.branch IS 'Bzr branch';


COMMENT ON COLUMN public.branch.summary IS 'A single paragraph description of the branch';


COMMENT ON COLUMN public.branch.home_page IS 'This column is deprecated and to be removed soon.';


COMMENT ON COLUMN public.branch.whiteboard IS 'Notes on the current status of the branch';


COMMENT ON COLUMN public.branch.lifecycle_status IS 'Authors assesment of the branchs maturity';


COMMENT ON COLUMN public.branch.last_mirrored IS 'The time when the branch was last mirrored.';


COMMENT ON COLUMN public.branch.mirror_status_message IS 'The last message we got when mirroring this branch.';


COMMENT ON COLUMN public.branch.last_scanned IS 'The time when the branch was last scanned.';


COMMENT ON COLUMN public.branch.last_scanned_id IS 'The revision ID of the branch when it was last scanned.';


COMMENT ON COLUMN public.branch.last_mirrored_id IS 'The revision ID of the branch when it was last mirrored.';


COMMENT ON COLUMN public.branch.revision_count IS 'The number of revisions in the associated bazaar branch revision_history.';


COMMENT ON COLUMN public.branch.next_mirror_time IS 'The time when we will next mirror this branch (NULL means never). This will be set automatically by pushing to a hosted branch, which, once mirrored, will be set back to NULL.';


COMMENT ON COLUMN public.branch.branch_type IS 'Branches are currently one of HOSTED (1), MIRRORED (2), or IMPORTED (3).';


COMMENT ON COLUMN public.branch.reviewer IS 'The reviewer (person or) team are able to transition merge proposals targetted at the branch throught the CODE_APPROVED state.';


COMMENT ON COLUMN public.branch.date_last_modified IS 'A branch is modified any time a user updates something using a view, a new revision for the branch is scanned, or the branch is linked to a bug, blueprint or merge proposal.';


COMMENT ON COLUMN public.branch.registrant IS 'The user that registered the branch.';


COMMENT ON COLUMN public.branch.branch_format IS 'The bzr branch format';


COMMENT ON COLUMN public.branch.repository_format IS 'The bzr repository format';


COMMENT ON COLUMN public.branch.metadir_format IS 'The bzr metadir format';


COMMENT ON COLUMN public.branch.stacked_on IS 'The Launchpad branch that this branch is stacked on (if any).';


COMMENT ON COLUMN public.branch.distroseries IS 'The distribution series that the branch belongs to.';


COMMENT ON COLUMN public.branch.sourcepackagename IS 'The source package this is a branch of.';


COMMENT ON COLUMN public.branch.size_on_disk IS 'The size in bytes of this branch in the mirrored area.';


COMMENT ON COLUMN public.branch.information_type IS 'Enum describing what type of information is stored, such as type of private or security related data, and used to determine how to apply an access policy.';


CREATE SEQUENCE public.branch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.branch_id_seq OWNED BY public.branch.id;


CREATE TABLE public.branchjob (
    id integer NOT NULL,
    job integer NOT NULL,
    branch integer,
    job_type integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.branchjob IS 'Contains references to jobs that are executed for a branch.';


COMMENT ON COLUMN public.branchjob.job IS 'A reference to a row in the Job table that has all the common job details.';


COMMENT ON COLUMN public.branchjob.branch IS 'The branch that this job is for.';


COMMENT ON COLUMN public.branchjob.job_type IS 'The type of job, like new revisions, or attribute change.';


COMMENT ON COLUMN public.branchjob.json_data IS 'Data that is specific to the type of job, whether this be the revisions to send email out for, or the changes that were recorded for the branch.';


CREATE SEQUENCE public.branchjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.branchjob_id_seq OWNED BY public.branchjob.id;


CREATE TABLE public.branchmergeproposal (
    id integer NOT NULL,
    registrant integer NOT NULL,
    source_branch integer,
    target_branch integer,
    dependent_branch integer,
    whiteboard text,
    date_merged timestamp without time zone,
    merged_revno integer,
    merge_reporter integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    commit_message text,
    queue_position integer,
    queue_status integer DEFAULT 1 NOT NULL,
    date_review_requested timestamp without time zone,
    reviewer integer,
    date_reviewed timestamp without time zone,
    reviewed_revision_id text,
    queuer integer,
    date_queued timestamp without time zone,
    queued_revision_id text,
    merger integer,
    merged_revision_id text,
    date_merge_started timestamp without time zone,
    date_merge_finished timestamp without time zone,
    merge_log_file integer,
    superseded_by integer,
    root_message_id text,
    description text,
    source_git_repository integer,
    source_git_path text,
    source_git_commit_sha1 character(40),
    target_git_repository integer,
    target_git_path text,
    target_git_commit_sha1 character(40),
    dependent_git_repository integer,
    dependent_git_path text,
    dependent_git_commit_sha1 character(40),
    CONSTRAINT consistent_dependent_git_ref CHECK ((((dependent_git_repository IS NULL) = (dependent_git_path IS NULL)) AND ((dependent_git_repository IS NULL) = (dependent_git_commit_sha1 IS NULL)))),
    CONSTRAINT consistent_source_git_ref CHECK ((((source_git_repository IS NULL) = (source_git_path IS NULL)) AND ((source_git_repository IS NULL) = (source_git_commit_sha1 IS NULL)))),
    CONSTRAINT consistent_target_git_ref CHECK ((((target_git_repository IS NULL) = (target_git_path IS NULL)) AND ((target_git_repository IS NULL) = (target_git_commit_sha1 IS NULL)))),
    CONSTRAINT different_branches CHECK ((((source_branch <> target_branch) AND (dependent_branch <> source_branch)) AND (dependent_branch <> target_branch))),
    CONSTRAINT different_git_refs CHECK (((source_git_repository IS NULL) OR ((((source_git_repository <> target_git_repository) OR (source_git_path <> target_git_path)) AND ((dependent_git_repository <> source_git_repository) OR (dependent_git_path <> source_git_path))) AND ((dependent_git_repository <> target_git_repository) OR (dependent_git_path <> target_git_path))))),
    CONSTRAINT one_vcs CHECK ((((((source_branch IS NOT NULL) AND (target_branch IS NOT NULL)) <> ((source_git_repository IS NOT NULL) AND (target_git_repository IS NOT NULL))) AND ((dependent_branch IS NULL) OR (source_branch IS NOT NULL))) AND ((dependent_git_repository IS NULL) OR (source_git_repository IS NOT NULL)))),
    CONSTRAINT positive_revno CHECK (((merged_revno IS NULL) OR (merged_revno > 0)))
);


COMMENT ON TABLE public.branchmergeproposal IS 'Branch merge proposals record the intent of landing (or merging) one branch on another.';


COMMENT ON COLUMN public.branchmergeproposal.registrant IS 'The person that created the merge proposal.';


COMMENT ON COLUMN public.branchmergeproposal.source_branch IS 'The branch where the work is being written.  This branch contains the changes that the registrant wants to land.';


COMMENT ON COLUMN public.branchmergeproposal.target_branch IS 'The branch where the user wants the changes from the source branch to be merged into.';


COMMENT ON COLUMN public.branchmergeproposal.dependent_branch IS 'If the source branch was not branched off the target branch, then this is considered the dependent_branch.';


COMMENT ON COLUMN public.branchmergeproposal.whiteboard IS 'Used to write other information about the branch, like test URLs.';


COMMENT ON COLUMN public.branchmergeproposal.date_merged IS 'This is the date that merge occurred.';


COMMENT ON COLUMN public.branchmergeproposal.merged_revno IS 'This is the revision number of the revision on the target branch that includes the merge from the source branch.';


COMMENT ON COLUMN public.branchmergeproposal.merge_reporter IS 'This is the user that marked the proposal as merged.';


COMMENT ON COLUMN public.branchmergeproposal.date_created IS 'When the registrant created the merge proposal.';


COMMENT ON COLUMN public.branchmergeproposal.commit_message IS 'This is the commit message that is to be used when the branch is landed by a robot.';


COMMENT ON COLUMN public.branchmergeproposal.queue_position IS 'The position on the merge proposal in the overall landing queue.  If the branch has a merge_robot set and the merge robot controls multiple branches then the queue position is unique over all the queued merge proposals for the landing robot.';


COMMENT ON COLUMN public.branchmergeproposal.queue_status IS 'This is the current state of the merge proposal.';


COMMENT ON COLUMN public.branchmergeproposal.date_review_requested IS 'The date that the merge proposal enters the REVIEW_REQUESTED state. This is stored so that we can determine how long a branch has been waiting for code approval.';


COMMENT ON COLUMN public.branchmergeproposal.reviewer IS 'The individual who said that the code in this branch is OK to land.';


COMMENT ON COLUMN public.branchmergeproposal.date_reviewed IS 'When the reviewer said the code is OK to land.';


COMMENT ON COLUMN public.branchmergeproposal.reviewed_revision_id IS 'The Bazaar revision ID that was approved to land.';


COMMENT ON COLUMN public.branchmergeproposal.queuer IS 'The individual who submitted the branch to the merge queue. This is usually the merge proposal registrant.';


COMMENT ON COLUMN public.branchmergeproposal.date_queued IS 'When the queuer submitted the branch to the merge queue.';


COMMENT ON COLUMN public.branchmergeproposal.queued_revision_id IS 'The Bazaar revision ID that is queued to land.';


COMMENT ON COLUMN public.branchmergeproposal.merger IS 'The merger is the person who merged the branch.';


COMMENT ON COLUMN public.branchmergeproposal.merged_revision_id IS 'The Bazaar revision ID that was actually merged.  If the owner of the source branch is a trusted person, this may be different than the revision_id that was actually queued or reviewed.';


COMMENT ON COLUMN public.branchmergeproposal.date_merge_started IS 'If the merge is performed by a bot the time the merge was started is recorded otherwise it is NULL.';


COMMENT ON COLUMN public.branchmergeproposal.date_merge_finished IS 'If the merge is performed by a bot the time the merge was finished is recorded otherwise it is NULL.';


COMMENT ON COLUMN public.branchmergeproposal.merge_log_file IS 'If the merge is performed by a bot the log file is accessible from the librarian.';


COMMENT ON COLUMN public.branchmergeproposal.superseded_by IS 'The proposal to merge has been superceded by this one.';


COMMENT ON COLUMN public.branchmergeproposal.root_message_id IS 'The root message of this BranchMergeProposal''s mail thread.';


CREATE SEQUENCE public.branchmergeproposal_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.branchmergeproposal_id_seq OWNED BY public.branchmergeproposal.id;


CREATE TABLE public.branchmergeproposaljob (
    id integer NOT NULL,
    job integer NOT NULL,
    branch_merge_proposal integer NOT NULL,
    job_type integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.branchmergeproposaljob IS 'Contains references to jobs that are executed for a branch merge proposal.';


COMMENT ON COLUMN public.branchmergeproposaljob.job IS 'A reference to a row in the Job table that has all the common job details.';


COMMENT ON COLUMN public.branchmergeproposaljob.branch_merge_proposal IS 'The branch merge proposal that this job is for.';


COMMENT ON COLUMN public.branchmergeproposaljob.job_type IS 'The type of job, like new proposal, review comment, or new review requested.';


COMMENT ON COLUMN public.branchmergeproposaljob.json_data IS 'Data that is specific to the type of job, normally references to code review messages and or votes.';


CREATE SEQUENCE public.branchmergeproposaljob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.branchmergeproposaljob_id_seq OWNED BY public.branchmergeproposaljob.id;


CREATE TABLE public.branchrevision (
    sequence integer,
    branch integer NOT NULL,
    revision integer NOT NULL
)
WITH (fillfactor='100');


CREATE TABLE public.branchsubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    branch integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    notification_level integer DEFAULT 1 NOT NULL,
    max_diff_lines integer,
    review_level integer DEFAULT 0 NOT NULL,
    subscribed_by integer NOT NULL
);


COMMENT ON TABLE public.branchsubscription IS 'An association between a person or team and a bazaar branch.';


COMMENT ON COLUMN public.branchsubscription.person IS 'The person or team associated with the branch.';


COMMENT ON COLUMN public.branchsubscription.branch IS 'The branch associated with the person or team.';


COMMENT ON COLUMN public.branchsubscription.notification_level IS 'The level of email the person wants to receive from branch updates.';


COMMENT ON COLUMN public.branchsubscription.max_diff_lines IS 'If the generated diff for a revision is larger than this number, then the diff is not sent in the notification email.';


COMMENT ON COLUMN public.branchsubscription.review_level IS 'The level of email the person wants to receive from review activity';


CREATE SEQUENCE public.branchsubscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.branchsubscription_id_seq OWNED BY public.branchsubscription.id;


CREATE SEQUENCE public.bug_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bug_id_seq OWNED BY public.bug.id;


CREATE TABLE public.bugactivity (
    id integer NOT NULL,
    bug integer NOT NULL,
    datechanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    whatchanged text NOT NULL,
    oldvalue text,
    newvalue text,
    message text
)
WITH (fillfactor='100');


CREATE SEQUENCE public.bugactivity_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugactivity_id_seq OWNED BY public.bugactivity.id;


CREATE TABLE public.bugaffectsperson (
    id integer NOT NULL,
    bug integer NOT NULL,
    person integer NOT NULL,
    affected boolean DEFAULT true NOT NULL
);


COMMENT ON TABLE public.bugaffectsperson IS 'This table maintains a mapping between bugs and users indicating that they are affected by that bug. The value is calculated and cached in the Bug.users_affected_count column.';


COMMENT ON COLUMN public.bugaffectsperson.bug IS 'The bug affecting this person.';


COMMENT ON COLUMN public.bugaffectsperson.person IS 'The person affected by this bug.';


CREATE SEQUENCE public.bugaffectsperson_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugaffectsperson_id_seq OWNED BY public.bugaffectsperson.id;


CREATE TABLE public.bugattachment (
    id integer NOT NULL,
    message integer NOT NULL,
    name text,
    title text,
    libraryfile integer NOT NULL,
    bug integer NOT NULL,
    type integer NOT NULL,
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


CREATE SEQUENCE public.bugattachment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugattachment_id_seq OWNED BY public.bugattachment.id;


CREATE TABLE public.bugbranch (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    bug integer NOT NULL,
    branch integer NOT NULL,
    revision_hint integer,
    whiteboard text,
    registrant integer NOT NULL
);


COMMENT ON TABLE public.bugbranch IS 'A branch related to a bug, most likely a branch for fixing the bug.';


COMMENT ON COLUMN public.bugbranch.bug IS 'The bug associated with this branch.';


COMMENT ON COLUMN public.bugbranch.branch IS 'The branch associated to the bug.';


COMMENT ON COLUMN public.bugbranch.revision_hint IS 'An optional revision at which this branch became interesting to this bug, and/or may contain a fix for the bug.';


COMMENT ON COLUMN public.bugbranch.whiteboard IS 'Additional information about the status of the bugfix in this branch.';


COMMENT ON COLUMN public.bugbranch.registrant IS 'The person who linked the bug to the branch.';


CREATE SEQUENCE public.bugbranch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugbranch_id_seq OWNED BY public.bugbranch.id;


CREATE TABLE public.bugmessage (
    id integer NOT NULL,
    bug integer NOT NULL,
    message integer NOT NULL,
    bugwatch integer,
    remote_comment_id text,
    index integer NOT NULL,
    owner integer NOT NULL,
    CONSTRAINT imported_comment CHECK (((remote_comment_id IS NULL) OR (bugwatch IS NOT NULL)))
);


COMMENT ON TABLE public.bugmessage IS 'This table maps a message to a bug. In other words, it shows that a particular message is associated with a particular bug.';


COMMENT ON COLUMN public.bugmessage.bugwatch IS 'The external bug this bug comment was imported from.';


COMMENT ON COLUMN public.bugmessage.remote_comment_id IS 'The id this bug comment has in the external bug tracker, if it is an imported comment. If it is NULL while having a bugwatch set, this comment was added in Launchpad and needs to be pushed to the external bug tracker.';


COMMENT ON COLUMN public.bugmessage.index IS 'The index (used in urls) of the message in a particular bug.';


COMMENT ON COLUMN public.bugmessage.owner IS 'Denormalised owner from Message, used for efficient queries on commentors.';


CREATE SEQUENCE public.bugmessage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugmessage_id_seq OWNED BY public.bugmessage.id;


CREATE TABLE public.bugmute (
    person integer NOT NULL,
    bug integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.bugmute IS 'Mutes for bug notifications.';


COMMENT ON COLUMN public.bugmute.person IS 'The person that muted all notifications from this bug.';


COMMENT ON COLUMN public.bugmute.bug IS 'The bug of this record';


COMMENT ON COLUMN public.bugmute.date_created IS 'The date at which this mute was created.';


CREATE TABLE public.bugnomination (
    id integer NOT NULL,
    bug integer NOT NULL,
    distroseries integer,
    productseries integer,
    status integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    date_decided timestamp without time zone,
    owner integer NOT NULL,
    decider integer,
    CONSTRAINT distroseries_or_productseries CHECK (((distroseries IS NULL) <> (productseries IS NULL)))
);


COMMENT ON TABLE public.bugnomination IS 'A bug nominated for fixing in a distroseries or productseries';


COMMENT ON COLUMN public.bugnomination.bug IS 'The bug being nominated.';


COMMENT ON COLUMN public.bugnomination.distroseries IS 'The distroseries for which the bug is nominated.';


COMMENT ON COLUMN public.bugnomination.productseries IS 'The productseries for which the bug is nominated.';


COMMENT ON COLUMN public.bugnomination.status IS 'The status of the nomination.';


COMMENT ON COLUMN public.bugnomination.date_created IS 'The date the nomination was submitted.';


COMMENT ON COLUMN public.bugnomination.date_decided IS 'The date the nomination was approved or declined.';


COMMENT ON COLUMN public.bugnomination.owner IS 'The person that submitted the nomination';


COMMENT ON COLUMN public.bugnomination.decider IS 'The person who approved or declined the nomination';


CREATE SEQUENCE public.bugnomination_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugnomination_id_seq OWNED BY public.bugnomination.id;


CREATE TABLE public.bugnotification (
    id integer NOT NULL,
    bug integer NOT NULL,
    message integer NOT NULL,
    is_comment boolean NOT NULL,
    date_emailed timestamp without time zone,
    status integer DEFAULT 10 NOT NULL,
    activity integer
);


COMMENT ON TABLE public.bugnotification IS 'The text representation of changes to a bug, which are used to send email notifications to bug changes.';


COMMENT ON COLUMN public.bugnotification.bug IS 'The bug that was changed.';


COMMENT ON COLUMN public.bugnotification.message IS 'The message the contains the textual representation of the change.';


COMMENT ON COLUMN public.bugnotification.is_comment IS 'Is the change a comment addition.';


COMMENT ON COLUMN public.bugnotification.date_emailed IS 'When this notification was emailed to the bug subscribers.';


COMMENT ON COLUMN public.bugnotification.status IS 'The status of this bug notification: pending, omitted, or sent.';


COMMENT ON COLUMN public.bugnotification.activity IS 'The BugActivity record corresponding to this notification, if any.';


CREATE SEQUENCE public.bugnotification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugnotification_id_seq OWNED BY public.bugnotification.id;


CREATE TABLE public.bugnotificationarchive (
    id integer NOT NULL,
    bug integer,
    message integer,
    is_comment boolean,
    date_emailed timestamp without time zone
);


CREATE TABLE public.bugnotificationattachment (
    id integer NOT NULL,
    message integer NOT NULL,
    bug_notification integer NOT NULL
);


COMMENT ON TABLE public.bugnotificationattachment IS 'Attachments to be attached to a bug notification.';


COMMENT ON COLUMN public.bugnotificationattachment.message IS 'A message to be attached to the sent bug notification. It will be attached as a mime/multipart part, with a content type of message/rfc822.';


COMMENT ON COLUMN public.bugnotificationattachment.bug_notification IS 'The bug notification, to which things should be attached to.';


CREATE SEQUENCE public.bugnotificationattachment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugnotificationattachment_id_seq OWNED BY public.bugnotificationattachment.id;


CREATE TABLE public.bugnotificationfilter (
    bug_notification integer NOT NULL,
    bug_subscription_filter integer NOT NULL
);


COMMENT ON TABLE public.bugnotificationfilter IS 'BugSubscriptionFilters that caused BugNotification to be generated.';


COMMENT ON COLUMN public.bugnotificationfilter.bug_notification IS 'The bug notification which a filter caused to be emitted.';


COMMENT ON COLUMN public.bugnotificationfilter.bug_subscription_filter IS 'A BugSubscriptionFilter that caused a notification to go off.';


CREATE TABLE public.bugnotificationrecipient (
    id integer NOT NULL,
    bug_notification integer NOT NULL,
    person integer NOT NULL,
    reason_header text NOT NULL,
    reason_body text NOT NULL
);


COMMENT ON TABLE public.bugnotificationrecipient IS 'The recipient for a bug notification.';


COMMENT ON COLUMN public.bugnotificationrecipient.bug_notification IS 'The notification this recipient should get.';


COMMENT ON COLUMN public.bugnotificationrecipient.person IS 'The person who should receive this notification.';


COMMENT ON COLUMN public.bugnotificationrecipient.reason_header IS 'The reason this person is receiving this notification (the value for the X-Launchpad-Message-Rationale header).';


COMMENT ON COLUMN public.bugnotificationrecipient.reason_body IS 'A line of text describing the reason this person is receiving this notification (to be included in the email message).';


CREATE SEQUENCE public.bugnotificationrecipient_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugnotificationrecipient_id_seq OWNED BY public.bugnotificationrecipient.id;


CREATE TABLE public.bugsubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    bug integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    subscribed_by integer NOT NULL,
    bug_notification_level integer DEFAULT 40 NOT NULL
);


COMMENT ON TABLE public.bugsubscription IS 'A subscription by a Person to a bug.';


COMMENT ON COLUMN public.bugsubscription.bug_notification_level IS 'The level of notifications which the Person will receive from this subscription.';


CREATE SEQUENCE public.bugsubscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugsubscription_id_seq OWNED BY public.bugsubscription.id;


CREATE TABLE public.bugsubscriptionfilter (
    id integer NOT NULL,
    structuralsubscription integer,
    find_all_tags boolean NOT NULL,
    include_any_tags boolean NOT NULL,
    exclude_any_tags boolean NOT NULL,
    other_parameters text,
    description text,
    bug_notification_level integer DEFAULT 40 NOT NULL
);


COMMENT ON TABLE public.bugsubscriptionfilter IS 'A filter with search criteria. Emails are sent only if the affected bug matches the specified parameters. The parameters are the same as those used for bugtask searches.';


COMMENT ON COLUMN public.bugsubscriptionfilter.structuralsubscription IS 'The structural subscription to be filtered.';


COMMENT ON COLUMN public.bugsubscriptionfilter.find_all_tags IS 'If set, search for bugs having all tags specified in BugSubscriptionFilterTag, else search for bugs having any of the tags specified in BugSubscriptionFilterTag.';


COMMENT ON COLUMN public.bugsubscriptionfilter.include_any_tags IS 'If True, include messages for bugs having any tag set.';


COMMENT ON COLUMN public.bugsubscriptionfilter.exclude_any_tags IS 'If True, exclude bugs having any tag set.';


COMMENT ON COLUMN public.bugsubscriptionfilter.other_parameters IS 'Other filter paremeters. Actual filtering is implemented on Python level.';


COMMENT ON COLUMN public.bugsubscriptionfilter.description IS 'A description of the filter, allowing subscribers to note the intent of the filter.';


COMMENT ON COLUMN public.bugsubscriptionfilter.bug_notification_level IS 'The volume and type of bug notifications this filter will allow. The value is an item of the enumeration `BugNotificationLevel`.';


CREATE SEQUENCE public.bugsubscriptionfilter_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugsubscriptionfilter_id_seq OWNED BY public.bugsubscriptionfilter.id;


CREATE TABLE public.bugsubscriptionfilterimportance (
    filter integer NOT NULL,
    importance integer NOT NULL
);


COMMENT ON TABLE public.bugsubscriptionfilterimportance IS 'Filter a bugsubscription by bug task status.';


COMMENT ON COLUMN public.bugsubscriptionfilterimportance.filter IS 'The subscription filter of this record.';


COMMENT ON COLUMN public.bugsubscriptionfilterimportance.importance IS 'The bug task importance.';


CREATE TABLE public.bugsubscriptionfilterinformationtype (
    filter integer NOT NULL,
    information_type integer NOT NULL
);


CREATE TABLE public.bugsubscriptionfiltermute (
    person integer NOT NULL,
    filter integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.bugsubscriptionfiltermute IS 'Mutes for subscription filters.';


COMMENT ON COLUMN public.bugsubscriptionfiltermute.person IS 'The person that muted their subscription to this filter.';


COMMENT ON COLUMN public.bugsubscriptionfiltermute.filter IS 'The subscription filter of this record';


COMMENT ON COLUMN public.bugsubscriptionfiltermute.date_created IS 'The date at which this mute was created.';


CREATE TABLE public.bugsubscriptionfilterstatus (
    filter integer NOT NULL,
    status integer NOT NULL
);


COMMENT ON TABLE public.bugsubscriptionfilterstatus IS 'Filter a bugsubscription by bug task status.';


COMMENT ON COLUMN public.bugsubscriptionfilterstatus.filter IS 'The subscription filter of this record.';


COMMENT ON COLUMN public.bugsubscriptionfilterstatus.status IS 'The bug task status.';


CREATE TABLE public.bugsubscriptionfiltertag (
    id integer NOT NULL,
    filter integer NOT NULL,
    tag text NOT NULL,
    include boolean NOT NULL
);


COMMENT ON TABLE public.bugsubscriptionfiltertag IS 'Filter by bug tag.';


COMMENT ON COLUMN public.bugsubscriptionfiltertag.filter IS 'The subscription filter of this record.';


COMMENT ON COLUMN public.bugsubscriptionfiltertag.tag IS 'A bug tag.';


COMMENT ON COLUMN public.bugsubscriptionfiltertag.include IS 'If True, send only messages for bugs having this tag, else send only messages for bugs which do not have this tag.';


CREATE SEQUENCE public.bugsubscriptionfiltertag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugsubscriptionfiltertag_id_seq OWNED BY public.bugsubscriptionfiltertag.id;


CREATE SEQUENCE public.bugsummary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugsummary_id_seq OWNED BY public.bugsummary.id;


CREATE TABLE public.bugsummaryjournal (
    id integer NOT NULL,
    count integer DEFAULT 0 NOT NULL,
    product integer,
    productseries integer,
    distribution integer,
    distroseries integer,
    sourcepackagename integer,
    viewed_by integer,
    tag text,
    status integer NOT NULL,
    milestone integer,
    importance integer NOT NULL,
    has_patch boolean NOT NULL,
    access_policy integer
);


CREATE SEQUENCE public.bugsummaryjournal_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugsummaryjournal_id_seq OWNED BY public.bugsummaryjournal.id;


CREATE SEQUENCE public.bugtag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugtag_id_seq OWNED BY public.bugtag.id;


CREATE TABLE public.bugtask (
    id integer NOT NULL,
    bug integer NOT NULL,
    product integer,
    distribution integer,
    distroseries integer,
    sourcepackagename integer,
    status integer NOT NULL,
    importance integer DEFAULT 5 NOT NULL,
    assignee integer,
    date_assigned timestamp without time zone,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    owner integer NOT NULL,
    milestone integer,
    bugwatch integer,
    targetnamecache text,
    date_confirmed timestamp without time zone,
    date_inprogress timestamp without time zone,
    date_closed timestamp without time zone,
    productseries integer,
    date_incomplete timestamp without time zone,
    date_left_new timestamp without time zone,
    date_triaged timestamp without time zone,
    date_fix_committed timestamp without time zone,
    date_fix_released timestamp without time zone,
    date_left_closed timestamp without time zone,
    date_milestone_set timestamp without time zone,
    CONSTRAINT bugtask_assignment_checks CHECK (
CASE
    WHEN (product IS NOT NULL) THEN ((((productseries IS NULL) AND (distribution IS NULL)) AND (distroseries IS NULL)) AND (sourcepackagename IS NULL))
    WHEN (productseries IS NOT NULL) THEN (((distribution IS NULL) AND (distroseries IS NULL)) AND (sourcepackagename IS NULL))
    WHEN (distribution IS NOT NULL) THEN (distroseries IS NULL)
    WHEN (distroseries IS NOT NULL) THEN true
    ELSE false
END)
);


COMMENT ON TABLE public.bugtask IS 'Links a given Bug to a particular (sourcepackagename, distro) or product.';


COMMENT ON COLUMN public.bugtask.bug IS 'The bug that is assigned to this (sourcepackagename, distro) or product.';


COMMENT ON COLUMN public.bugtask.product IS 'The product in which this bug shows up.';


COMMENT ON COLUMN public.bugtask.distribution IS 'The distro of the named sourcepackage.';


COMMENT ON COLUMN public.bugtask.sourcepackagename IS 'The name of the sourcepackage in which this bug shows up.';


COMMENT ON COLUMN public.bugtask.status IS 'The general health of the bug, e.g. Accepted, Rejected, etc.';


COMMENT ON COLUMN public.bugtask.importance IS 'The importance of fixing the bug.';


COMMENT ON COLUMN public.bugtask.assignee IS 'The person who has been assigned to fix this bug in this product or (sourcepackagename, distro)';


COMMENT ON COLUMN public.bugtask.date_assigned IS 'The date on which the bug in this (sourcepackagename, distro) or product was assigned to someone to fix';


COMMENT ON COLUMN public.bugtask.datecreated IS 'A timestamp for the creation of this bug assignment. Note that this is not the date the bug was created (though it might be), it''s the date the bug was assigned to this product, which could have come later.';


COMMENT ON COLUMN public.bugtask.milestone IS 'A way to mark a bug for grouping purposes, e.g. to say it needs to be fixed by version 1.2';


COMMENT ON COLUMN public.bugtask.bugwatch IS 'This column allows us to link a bug
task to a bug watch. In other words, we are connecting the state of the task
to the state of the bug in a different bug tracking system. To the best of
our ability we''ll try and keep the bug task syncronised with the state of
the remote bug watch.';


COMMENT ON COLUMN public.bugtask.targetnamecache IS 'A cached value of the target name of this bugtask, to make it easier to sort and search on the target name.';


COMMENT ON COLUMN public.bugtask.date_confirmed IS 'The date when this bug transitioned from an unconfirmed status to a confirmed one. If the state regresses to a one that logically occurs before Confirmed, e.g., Unconfirmed, this date is cleared.';


COMMENT ON COLUMN public.bugtask.date_inprogress IS 'The date on which this bug transitioned from not being in progress to a state >= In Progress. If the status moves back to a pre-In Progress state, this date is cleared';


COMMENT ON COLUMN public.bugtask.date_closed IS 'The date when this bug transitioned to a resolved state, e.g., Rejected, Fix Released, etc. If the state changes back to a pre-closed state, this date is cleared';


COMMENT ON COLUMN public.bugtask.productseries IS 'The product series to which the bug is targeted';


COMMENT ON COLUMN public.bugtask.date_left_new IS 'The date when this bug first transitioned out of the NEW status.';


COMMENT ON COLUMN public.bugtask.date_triaged IS 'The date when this bug transitioned to a status >= TRIAGED.';


COMMENT ON COLUMN public.bugtask.date_fix_committed IS 'The date when this bug transitioned to a status >= FIXCOMMITTED.';


COMMENT ON COLUMN public.bugtask.date_fix_released IS 'The date when this bug transitioned to a FIXRELEASED status.';


COMMENT ON COLUMN public.bugtask.date_left_closed IS 'The date when this bug last transitioned out of a CLOSED status.';


COMMENT ON COLUMN public.bugtask.date_milestone_set IS 'The date when this bug was targed to the milestone that is currently set.';


CREATE SEQUENCE public.bugtask_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugtask_id_seq OWNED BY public.bugtask.id;


CREATE TABLE public.bugtracker (
    id integer NOT NULL,
    bugtrackertype integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text,
    baseurl text NOT NULL,
    owner integer NOT NULL,
    contactdetails text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    version text,
    block_comment_pushing boolean DEFAULT false NOT NULL,
    has_lp_plugin boolean,
    active boolean DEFAULT true NOT NULL,
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.bugtracker IS 'A bug tracker in some other project. Malone allows us to link Malone bugs with bugs recorded in other bug tracking systems, and to keep the status of the relevant bug task in sync with the status in that upstream bug tracker. So, for example, you might note that Malone bug #43224 is the same as a bug in the Apache bugzilla, number 534536. Then when the upstream guys mark that bug fixed in their bugzilla, Malone know that the bug is fixed upstream.';


COMMENT ON COLUMN public.bugtracker.bugtrackertype IS 'The type of bug tracker, a pointer to the table of bug tracker types. Currently we know about debbugs and bugzilla bugtrackers, and plan to support roundup and sourceforge as well.';


COMMENT ON COLUMN public.bugtracker.name IS 'The unique name of this bugtracker, allowing us to refer to it directly.';


COMMENT ON COLUMN public.bugtracker.title IS 'A title for the bug tracker, used in listings of all the bug trackers and also displayed at the top of the descriptive page for the bug tracker.';


COMMENT ON COLUMN public.bugtracker.summary IS 'A brief summary of this bug tracker, which might for example list any interesting policies regarding the use of the bug tracker. The summary is displayed in bold at the top of the bug tracker page.';


COMMENT ON COLUMN public.bugtracker.baseurl IS 'The base URL for this bug tracker. Using our knowledge of the bugtrackertype, and the details in the BugWatch table we are then able to calculate relative URLs for relevant pages in the bug tracker based on this baseurl.';


COMMENT ON COLUMN public.bugtracker.owner IS 'The person who created this bugtracker entry and who thus has permission to modify it. Ideally we would like this to be the person who coordinates the running of the actual bug tracker upstream.';


COMMENT ON COLUMN public.bugtracker.contactdetails IS 'The contact details of the people responsible for that bug tracker. This allows us to coordinate the syncing of bugs to and from that bug tracker with the responsible people on the other side.';


COMMENT ON COLUMN public.bugtracker.version IS 'The version of the bug tracker software being used.';


COMMENT ON COLUMN public.bugtracker.block_comment_pushing IS 'Whether to block pushing comments to the bug tracker. Having a value of false means that we will push the comments if the bug tracker supports it.';


COMMENT ON COLUMN public.bugtracker.has_lp_plugin IS 'Whether we have confirmed that the Launchpad plugin was installed on the bug tracker, the last time checkwatches was run.';


CREATE SEQUENCE public.bugtracker_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugtracker_id_seq OWNED BY public.bugtracker.id;


CREATE TABLE public.bugtrackeralias (
    id integer NOT NULL,
    bugtracker integer NOT NULL,
    base_url text NOT NULL
);


COMMENT ON TABLE public.bugtrackeralias IS 'A bugtracker alias is a URL that also refers to the same bugtracker as the master bugtracker. For example, a bugtracker might be accessible as both http://www.bugsrus.com/ and http://bugsrus.com/. A bugtracker can have many aliases, and all of them are checked to prevents users registering duplicate bugtrackers inadvertently.';


COMMENT ON COLUMN public.bugtrackeralias.bugtracker IS 'The master bugtracker that this alias refers to.';


COMMENT ON COLUMN public.bugtrackeralias.base_url IS 'Another base URL for this bug tracker. See BugTracker.baseurl.';


CREATE SEQUENCE public.bugtrackeralias_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugtrackeralias_id_seq OWNED BY public.bugtrackeralias.id;


CREATE TABLE public.bugtrackercomponent (
    id integer NOT NULL,
    name text NOT NULL,
    is_visible boolean DEFAULT true NOT NULL,
    is_custom boolean DEFAULT true NOT NULL,
    component_group integer NOT NULL,
    distribution integer,
    source_package_name integer,
    CONSTRAINT valid_target CHECK (((distribution IS NULL) = (source_package_name IS NULL)))
);


COMMENT ON TABLE public.bugtrackercomponent IS 'A software component in a remote bug tracker, which can be linked to the corresponding source package in a distribution using this table.';


COMMENT ON COLUMN public.bugtrackercomponent.name IS 'The name of the component as registered in the remote bug tracker.';


COMMENT ON COLUMN public.bugtrackercomponent.is_visible IS 'Whether to display or hide the item in the Launchpad user interface.';


COMMENT ON COLUMN public.bugtrackercomponent.is_custom IS 'Whether the item was added by a user in Launchpad or is kept in sync with the remote bug tracker.';


COMMENT ON COLUMN public.bugtrackercomponent.component_group IS 'The product or other higher level category used by the remote bug tracker to group projects, if any.';


COMMENT ON COLUMN public.bugtrackercomponent.distribution IS 'Link to the distribution for the associated source package.  This can be NULL if no ling has been established.';


COMMENT ON COLUMN public.bugtrackercomponent.source_package_name IS 'The text name of the source package in a distribution that corresponds to this component.  This can be NULL if no link has been established yet.';


CREATE SEQUENCE public.bugtrackercomponent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugtrackercomponent_id_seq OWNED BY public.bugtrackercomponent.id;


CREATE TABLE public.bugtrackercomponentgroup (
    id integer NOT NULL,
    name text NOT NULL,
    bug_tracker integer NOT NULL
);


COMMENT ON TABLE public.bugtrackercomponentgroup IS 'A collection of components as modeled in a remote bug tracker, often referred to as a product.  Some bug trackers do not categorize software components this way, so they will have a single default component group that all components belong to.';


COMMENT ON COLUMN public.bugtrackercomponentgroup.name IS 'The product or category name used in the remote bug tracker for grouping components.';


COMMENT ON COLUMN public.bugtrackercomponentgroup.bug_tracker IS 'The external bug tracker this component group belongs to.';


CREATE SEQUENCE public.bugtrackercomponentgroup_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugtrackercomponentgroup_id_seq OWNED BY public.bugtrackercomponentgroup.id;


CREATE TABLE public.bugtrackerperson (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    bugtracker integer NOT NULL,
    person integer NOT NULL,
    name text NOT NULL
);


COMMENT ON TABLE public.bugtrackerperson IS 'A mapping from a user in an external bug tracker to a Person record in Launchpad. This is used when we can''t get an email address from the bug tracker.';


COMMENT ON COLUMN public.bugtrackerperson.date_created IS 'When was this mapping added.';


COMMENT ON COLUMN public.bugtrackerperson.bugtracker IS 'The external bug tracker in which this user has an account.';


COMMENT ON COLUMN public.bugtrackerperson.person IS 'The Person record in Launchpad this user corresponds to.';


COMMENT ON COLUMN public.bugtrackerperson.name IS 'The (within the bug tracker) unique username in the external bug tracker.';


CREATE SEQUENCE public.bugtrackerperson_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugtrackerperson_id_seq OWNED BY public.bugtrackerperson.id;


CREATE TABLE public.bugwatch (
    id integer NOT NULL,
    bug integer NOT NULL,
    bugtracker integer NOT NULL,
    remotebug text NOT NULL,
    remotestatus text,
    lastchanged timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    lastchecked timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    owner integer NOT NULL,
    last_error_type integer,
    remote_importance text,
    remote_lp_bug_id integer,
    next_check timestamp without time zone
);


COMMENT ON COLUMN public.bugwatch.last_error_type IS 'The type of error which last prevented this entry from being updated. Legal values are defined by the BugWatchErrorType enumeration.';


COMMENT ON COLUMN public.bugwatch.remote_importance IS 'The importance of the bug as returned by the remote server. This will be converted into a Launchpad BugTaskImportance value.';


COMMENT ON COLUMN public.bugwatch.remote_lp_bug_id IS 'The bug in Launchpad that the remote bug is pointing at. This can be different than the BugWatch.bug column, since the same remote bug can be linked from multiple bugs in Launchpad, but the remote bug can only link to a single bug in Launchpad. The main use case for this column is to avoid having to query the remote bug tracker for this information, in order to decide whether we need to give this information to the remote bug tracker.';


COMMENT ON COLUMN public.bugwatch.next_check IS 'The time after which the watch should next be checked. Note that this does not denote an exact schedule for the next check since checkwatches only runs periodically.';


CREATE SEQUENCE public.bugwatch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugwatch_id_seq OWNED BY public.bugwatch.id;


CREATE TABLE public.bugwatchactivity (
    id integer NOT NULL,
    bug_watch integer NOT NULL,
    activity_date timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    result integer NOT NULL,
    message text,
    oops_id text
)
WITH (fillfactor='100');


COMMENT ON TABLE public.bugwatchactivity IS 'This table contains a record of each update for a given bug watch. This allows us to track whether a given update was successful or not and, if not, the details of the error which caused the update to fail.';


COMMENT ON COLUMN public.bugwatchactivity.bug_watch IS 'The bug_watch to which this activity entry relates.';


COMMENT ON COLUMN public.bugwatchactivity.activity_date IS 'The datetime at which the activity occurred.';


COMMENT ON COLUMN public.bugwatchactivity.result IS 'The result of the update. Legal values are defined in the BugWatchErrorType enumeration. An update is considered successful if its error_type is NULL.';


COMMENT ON COLUMN public.bugwatchactivity.message IS 'The message (if any) associated with the update.';


COMMENT ON COLUMN public.bugwatchactivity.oops_id IS 'The OOPS id, if any, associated with the error that caused the update to fail.';


CREATE SEQUENCE public.bugwatchactivity_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bugwatchactivity_id_seq OWNED BY public.bugwatchactivity.id;


CREATE TABLE public.builder (
    id integer NOT NULL,
    processor integer,
    name text NOT NULL,
    title text NOT NULL,
    owner integer NOT NULL,
    speedindex integer,
    builderok boolean NOT NULL,
    failnotes text,
    virtualized boolean DEFAULT true NOT NULL,
    url text NOT NULL,
    manual boolean DEFAULT false,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    vm_host text,
    active boolean DEFAULT true NOT NULL,
    failure_count integer DEFAULT 0 NOT NULL,
    version text,
    clean_status integer DEFAULT 1 NOT NULL,
    vm_reset_protocol integer,
    date_clean_status_changed timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT valid_absolute_url CHECK (public.valid_absolute_url(url))
);


COMMENT ON TABLE public.builder IS 'Builder: This table stores the build-slave registry and status information as: name, url, trusted, builderok, builderaction, failnotes.';


COMMENT ON COLUMN public.builder.speedindex IS 'A relative measure of the speed of this builder. If NULL, we do not yet have a speedindex for the builder else it is the number of seconds needed to perform a reference build';


COMMENT ON COLUMN public.builder.builderok IS 'Should a builder fail for any reason, from out-of-disk-space to not responding to the buildd master, the builderok flag is set to false and the failnotes column is filled with a reason.';


COMMENT ON COLUMN public.builder.failnotes IS 'This column gets filled out with a textual description of how/why a builder has failed. If the builderok column is true then the value in this column is irrelevant and should be treated as NULL or empty.';


COMMENT ON COLUMN public.builder.virtualized IS 'Whether or not the builder is a virtual Xen builder. Packages coming via ubuntu workflow are trusted to build on non-Xen and do not need facist behaviour to be built. Other packages like ppa/grumpy incoming packages can contain malicious code, so are unstrusted and build in a Xen virtual machine.';


COMMENT ON COLUMN public.builder.url IS 'The url to the build slave. There may be more than one build slave on a given host so this url includes the port number to use. The default port number for a build slave is 8221';


COMMENT ON COLUMN public.builder.manual IS 'Whether or not builder was manual mode, i.e., collect any result from the it, but do not dispach anything to it automatically.';


COMMENT ON COLUMN public.builder.vm_host IS 'The virtual machine host associated to this builder. It should be empty for "native" builders (old fashion or architectures not yet supported by XEN).';


COMMENT ON COLUMN public.builder.active IS 'Whether to present or not the builder in the public list of builders avaialble. It is used to hide transient or defunct builders while they get fixed.';


COMMENT ON COLUMN public.builder.failure_count IS 'The number of consecutive failures on this builder.  Is reset to zero after a sucessful dispatch.';


COMMENT ON COLUMN public.builder.version IS 'The version of launchpad-buildd on the slave.';


CREATE SEQUENCE public.builder_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.builder_id_seq OWNED BY public.builder.id;


CREATE TABLE public.builderprocessor (
    builder integer NOT NULL,
    processor integer NOT NULL
);


CREATE TABLE public.buildfarmjob (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_finished timestamp without time zone,
    builder integer,
    status integer NOT NULL,
    job_type integer NOT NULL,
    archive integer
);


COMMENT ON TABLE public.buildfarmjob IS 'BuildFarmJob: This table stores the information common to all jobs on the Launchpad build farm.';


COMMENT ON COLUMN public.buildfarmjob.date_created IS 'When the build farm job record was created.';


COMMENT ON COLUMN public.buildfarmjob.date_finished IS 'When the build farm job finished being processed.';


COMMENT ON COLUMN public.buildfarmjob.builder IS 'Points to the builder which processed this build farm job.';


COMMENT ON COLUMN public.buildfarmjob.status IS 'Stores the current build status.';


COMMENT ON COLUMN public.buildfarmjob.job_type IS 'The type of build farm job to which this record corresponds.';


CREATE SEQUENCE public.buildfarmjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.buildfarmjob_id_seq OWNED BY public.buildfarmjob.id;


CREATE TABLE public.buildqueue (
    id integer NOT NULL,
    builder integer,
    logtail text,
    lastscore integer,
    manual boolean DEFAULT false NOT NULL,
    estimated_duration interval DEFAULT '00:00:00'::interval NOT NULL,
    processor integer,
    virtualized boolean NOT NULL,
    build_farm_job integer NOT NULL,
    status integer NOT NULL,
    date_started timestamp without time zone
);


COMMENT ON TABLE public.buildqueue IS 'BuildQueue: The queue of jobs in progress/scheduled to run on the Soyuz build farm.';


COMMENT ON COLUMN public.buildqueue.builder IS 'The builder assigned to this build. Some builds will have a builder assigned to queue them up; some will be building on the specified builder already; others will not have a builder yet (NULL) and will be waiting to be assigned into a builder''s queue';


COMMENT ON COLUMN public.buildqueue.logtail IS 'The tail end of the log of the current build. This is updated regularly as the buildd master polls the buildd slaves. Once the build is complete; the full log will be lodged with the librarian and linked into the build table.';


COMMENT ON COLUMN public.buildqueue.lastscore IS 'The last score ascribed to this build record. This can be used in the UI among other places.';


COMMENT ON COLUMN public.buildqueue.manual IS 'Indicates if the current record was or not rescored manually, if so it get skipped from the auto-score procedure.';


COMMENT ON COLUMN public.buildqueue.estimated_duration IS 'Estimated job duration, based on previous running times of comparable jobs.';


COMMENT ON COLUMN public.buildqueue.processor IS 'The processor required by the associated build farm job.';


COMMENT ON COLUMN public.buildqueue.virtualized IS 'The virtualization setting required by the associated build farm job.';


CREATE SEQUENCE public.buildqueue_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.buildqueue_id_seq OWNED BY public.buildqueue.id;


CREATE TABLE public.codeimport (
    id integer NOT NULL,
    branch integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    rcs_type integer NOT NULL,
    cvs_root text,
    cvs_module text,
    review_status integer DEFAULT 1 NOT NULL,
    date_last_successful timestamp without time zone,
    owner integer NOT NULL,
    assignee integer,
    update_interval interval,
    url text,
    git_repository integer,
    CONSTRAINT one_target_vcs CHECK (((branch IS NOT NULL) <> (git_repository IS NOT NULL))),
    CONSTRAINT valid_source_target_vcs_pairing CHECK (((branch IS NOT NULL) OR (rcs_type = 4))),
    CONSTRAINT valid_vcs_details CHECK (
CASE
    WHEN (rcs_type = 1) THEN (((((cvs_root IS NOT NULL) AND (cvs_root <> ''::text)) AND (cvs_module IS NOT NULL)) AND (cvs_module <> ''::text)) AND (url IS NULL))
    WHEN (rcs_type = ANY (ARRAY[2, 3])) THEN ((((cvs_root IS NULL) AND (cvs_module IS NULL)) AND (url IS NOT NULL)) AND public.valid_absolute_url(url))
    WHEN (rcs_type = ANY (ARRAY[4, 5, 6])) THEN (((cvs_root IS NULL) AND (cvs_module IS NULL)) AND (url IS NOT NULL))
    ELSE false
END)
);


COMMENT ON TABLE public.codeimport IS 'The persistent record of an import from a foreign version control system to Bazaar, from the initial request to the regularly updated import branch.';


COMMENT ON COLUMN public.codeimport.branch IS 'The Bazaar branch produced by the import system.  Always non-NULL: a placeholder branch is created when the import is created.  The import is associated to a Product and Series though the branch.';


COMMENT ON COLUMN public.codeimport.registrant IS 'The person who originally requested this import.';


COMMENT ON COLUMN public.codeimport.rcs_type IS 'The revision control system used by the import source. The value is defined in dbschema.RevisionControlSystems.';


COMMENT ON COLUMN public.codeimport.cvs_root IS 'The $CVSROOT details, probably of the form :pserver:user@host:/path.';


COMMENT ON COLUMN public.codeimport.cvs_module IS 'The module in cvs_root to import, often the name of the project.';


COMMENT ON COLUMN public.codeimport.review_status IS 'Whether this code import request has been reviewed, and whether it was accepted.';


COMMENT ON COLUMN public.codeimport.date_last_successful IS 'When this code import last succeeded. NULL if this import has never succeeded.';


COMMENT ON COLUMN public.codeimport.owner IS 'The person who is currently responsible for keeping the import details up to date, initially set to the registrant. This person can edit some of the details of the code import branch.';


COMMENT ON COLUMN public.codeimport.assignee IS 'The person in charge of delivering this code import and interacting with the owner.';


COMMENT ON COLUMN public.codeimport.update_interval IS 'How often should this import be updated. If NULL, defaults to a system-wide value set by the Launchpad administrators.';


COMMENT ON COLUMN public.codeimport.url IS 'The URL of the foreign VCS branch for this import.';


COMMENT ON COLUMN public.codeimport.git_repository IS 'The Git repository produced by the import system, if applicable.  A placeholder repository is created when the import is created.  The import is associated with a target through the repository.';


CREATE SEQUENCE public.codeimport_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.codeimport_id_seq OWNED BY public.codeimport.id;


CREATE TABLE public.codeimportevent (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    entry_type integer NOT NULL,
    code_import integer,
    person integer,
    machine integer
);


COMMENT ON TABLE public.codeimportevent IS 'A record of events in the code import system.  Rows in this table are created by triggers on other code import tables.';


COMMENT ON COLUMN public.codeimportevent.entry_type IS 'The type of event that is recorded by this entry. Legal values are defined by the CodeImportEventType enumeration.';


COMMENT ON COLUMN public.codeimportevent.code_import IS 'The code import that was associated to this event, if any and if it has not been deleted.';


COMMENT ON COLUMN public.codeimportevent.person IS 'The user who caused the event, if the event is not automatically generated.';


COMMENT ON COLUMN public.codeimportevent.machine IS 'The code import machine that was concerned by this event, if any.';


CREATE SEQUENCE public.codeimportevent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.codeimportevent_id_seq OWNED BY public.codeimportevent.id;


CREATE TABLE public.codeimporteventdata (
    id integer NOT NULL,
    event integer,
    data_type integer NOT NULL,
    data_value text
);


COMMENT ON TABLE public.codeimporteventdata IS 'Additional data associated to a particular code import event.';


COMMENT ON COLUMN public.codeimporteventdata.event IS 'The event the data is associated to.';


COMMENT ON COLUMN public.codeimporteventdata.data_type IS 'The type of additional data, from the CodeImportEventDataType enumeration.';


COMMENT ON COLUMN public.codeimporteventdata.data_value IS 'The value of the additional data.  A string.';


CREATE SEQUENCE public.codeimporteventdata_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.codeimporteventdata_id_seq OWNED BY public.codeimporteventdata.id;


CREATE TABLE public.codeimportjob (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    code_import integer NOT NULL,
    machine integer,
    date_due timestamp without time zone NOT NULL,
    state integer NOT NULL,
    requesting_user integer,
    ordering integer,
    heartbeat timestamp without time zone,
    logtail text,
    date_started timestamp without time zone,
    CONSTRAINT valid_state CHECK (
CASE
    WHEN (state = 10) THEN (((((machine IS NULL) AND (ordering IS NULL)) AND (heartbeat IS NULL)) AND (date_started IS NULL)) AND (logtail IS NULL))
    WHEN (state = 20) THEN (((((machine IS NOT NULL) AND (ordering IS NOT NULL)) AND (heartbeat IS NULL)) AND (date_started IS NULL)) AND (logtail IS NULL))
    WHEN (state = 30) THEN (((((machine IS NOT NULL) AND (ordering IS NULL)) AND (heartbeat IS NOT NULL)) AND (date_started IS NOT NULL)) AND (logtail IS NOT NULL))
    ELSE false
END)
);


COMMENT ON TABLE public.codeimportjob IS 'A pending or active code import job.  There is always such a row for any active import, but it will not run until date_due is in the past.';


COMMENT ON COLUMN public.codeimportjob.code_import IS 'The code import that is being worked upon.';


COMMENT ON COLUMN public.codeimportjob.machine IS 'The machine job is currently scheduled to run on, or where the job is currently running.';


COMMENT ON COLUMN public.codeimportjob.date_due IS 'When the import should happen.';


COMMENT ON COLUMN public.codeimportjob.state IS 'One of PENDING (waiting until its due or a machine is online), SCHEDULED (assigned to a machine, but not yet running) or RUNNING (actually in the process of being imported now).';


COMMENT ON COLUMN public.codeimportjob.requesting_user IS 'The user who requested the import, if any. Set if and only if reason = REQUEST.';


COMMENT ON COLUMN public.codeimportjob.ordering IS 'A measure of how urgent the job is -- queue entries with lower "ordering" should be processed first, or in other works "ORDER BY ordering" returns the most import jobs first.';


COMMENT ON COLUMN public.codeimportjob.heartbeat IS 'While the job is running, this field should be updated frequently to indicate that the import job hasn''t crashed.';


COMMENT ON COLUMN public.codeimportjob.logtail IS 'The last few lines of output produced by the running job. It should be updated at the same time as the heartbeat.';


COMMENT ON COLUMN public.codeimportjob.date_started IS 'When the import began to be processed.';


CREATE SEQUENCE public.codeimportjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.codeimportjob_id_seq OWNED BY public.codeimportjob.id;


CREATE TABLE public.codeimportmachine (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    hostname text NOT NULL,
    state integer DEFAULT 10 NOT NULL,
    heartbeat timestamp without time zone
);


COMMENT ON TABLE public.codeimportmachine IS 'The record of a machine capable of performing jobs for the code import system.';


COMMENT ON COLUMN public.codeimportmachine.hostname IS 'The (unique) hostname of the machine.';


COMMENT ON COLUMN public.codeimportmachine.state IS 'Whether the controller daemon on this machine is offline, online, or quiescing (running but not accepting new jobs).';


COMMENT ON COLUMN public.codeimportmachine.heartbeat IS 'When the code-import-controller daemon was last known to be running on this machine. If it is not updated for a long time the machine state will change to offline.';


CREATE SEQUENCE public.codeimportmachine_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.codeimportmachine_id_seq OWNED BY public.codeimportmachine.id;


CREATE TABLE public.codeimportresult (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    code_import integer,
    machine integer,
    requesting_user integer,
    log_excerpt text,
    log_file integer,
    status integer NOT NULL,
    date_job_started timestamp without time zone
);


COMMENT ON TABLE public.codeimportresult IS 'A completed code import job.';


COMMENT ON COLUMN public.codeimportresult.code_import IS 'The code import for which the job was run.';


COMMENT ON COLUMN public.codeimportresult.machine IS 'The machine the job ran on.';


COMMENT ON COLUMN public.codeimportresult.log_excerpt IS 'The last few lines of the partial log, in case it is set.';


COMMENT ON COLUMN public.codeimportresult.log_file IS 'A partial log of the job for users to see. It is normally only recorded if the job failed in a step that interacts with the remote repository. If a job was successful, or failed in a houskeeping step, the log file would not contain information useful to the user.';


COMMENT ON COLUMN public.codeimportresult.status IS 'How the job ended. Success, some kind of failure, or some kind of interruption before completion.';


COMMENT ON COLUMN public.codeimportresult.date_job_started IS 'When the job started to run (date_created is when it finished).';


CREATE SEQUENCE public.codeimportresult_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.codeimportresult_id_seq OWNED BY public.codeimportresult.id;


CREATE TABLE public.codereviewinlinecomment (
    previewdiff integer NOT NULL,
    person integer NOT NULL,
    comment integer NOT NULL,
    comments text NOT NULL
);


CREATE TABLE public.codereviewinlinecommentdraft (
    previewdiff integer NOT NULL,
    person integer NOT NULL,
    comments text NOT NULL
);


CREATE TABLE public.codereviewmessage (
    id integer NOT NULL,
    branch_merge_proposal integer NOT NULL,
    message integer NOT NULL,
    vote integer,
    vote_tag text
);


COMMENT ON TABLE public.codereviewmessage IS 'A message that is part of a code review discussion.';


COMMENT ON COLUMN public.codereviewmessage.branch_merge_proposal IS 'The merge proposal that is being discussed.';


COMMENT ON COLUMN public.codereviewmessage.message IS 'The actual message.';


COMMENT ON COLUMN public.codereviewmessage.vote IS 'The reviewer''s vote for this message.';


COMMENT ON COLUMN public.codereviewmessage.vote_tag IS 'A short description of the vote';


CREATE SEQUENCE public.codereviewmessage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.codereviewmessage_id_seq OWNED BY public.codereviewmessage.id;


CREATE TABLE public.codereviewvote (
    id integer NOT NULL,
    branch_merge_proposal integer NOT NULL,
    reviewer integer NOT NULL,
    review_type text,
    registrant integer NOT NULL,
    vote_message integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.codereviewvote IS 'Reference to a person''s last vote in a code review discussion.';


COMMENT ON COLUMN public.codereviewvote.branch_merge_proposal IS 'The BranchMergeProposal for the code review.';


COMMENT ON COLUMN public.codereviewvote.reviewer IS 'The person performing the review.';


COMMENT ON COLUMN public.codereviewvote.review_type IS 'The aspect of the code being reviewed.';


COMMENT ON COLUMN public.codereviewvote.registrant IS 'The person who registered this vote';


COMMENT ON COLUMN public.codereviewvote.vote_message IS 'The message associated with the vote';


COMMENT ON COLUMN public.codereviewvote.date_created IS 'The date this vote reference was created';


CREATE SEQUENCE public.codereviewvote_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.codereviewvote_id_seq OWNED BY public.codereviewvote.id;


CREATE VIEW public.combinedbugsummary AS
 SELECT bugsummary.id,
    bugsummary.count,
    bugsummary.product,
    bugsummary.productseries,
    bugsummary.distribution,
    bugsummary.distroseries,
    bugsummary.sourcepackagename,
    bugsummary.viewed_by,
    bugsummary.tag,
    bugsummary.status,
    bugsummary.milestone,
    bugsummary.importance,
    bugsummary.has_patch,
    bugsummary.access_policy
   FROM public.bugsummary
UNION ALL
 SELECT (- bugsummaryjournal.id) AS id,
    bugsummaryjournal.count,
    bugsummaryjournal.product,
    bugsummaryjournal.productseries,
    bugsummaryjournal.distribution,
    bugsummaryjournal.distroseries,
    bugsummaryjournal.sourcepackagename,
    bugsummaryjournal.viewed_by,
    bugsummaryjournal.tag,
    bugsummaryjournal.status,
    bugsummaryjournal.milestone,
    bugsummaryjournal.importance,
    bugsummaryjournal.has_patch,
    bugsummaryjournal.access_policy
   FROM public.bugsummaryjournal;


CREATE TABLE public.commercialsubscription (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_starts timestamp without time zone NOT NULL,
    date_expires timestamp without time zone NOT NULL,
    status integer DEFAULT 10 NOT NULL,
    product integer NOT NULL,
    registrant integer NOT NULL,
    purchaser integer NOT NULL,
    whiteboard text,
    sales_system_id text
);


COMMENT ON TABLE public.commercialsubscription IS 'A Commercial Subscription entry for a project.  Projects with licenses of Other/Proprietary must purchase a subscription in order to use Launchpad.';


COMMENT ON COLUMN public.commercialsubscription.date_created IS 'The date this subscription was created in Launchpad.';


COMMENT ON COLUMN public.commercialsubscription.date_last_modified IS 'The date this subscription was last modified.';


COMMENT ON COLUMN public.commercialsubscription.date_starts IS 'The beginning date for this subscription.  It is invalid until that date.';


COMMENT ON COLUMN public.commercialsubscription.date_expires IS 'The expiration date for this subscription.  It is invalid after that date.';


COMMENT ON COLUMN public.commercialsubscription.status IS 'The current status.  One of: SUBSCRIBED, LAPSED, SUSPENDED.';


COMMENT ON COLUMN public.commercialsubscription.product IS 'The product this subscription enables.';


COMMENT ON COLUMN public.commercialsubscription.registrant IS 'The person who created this subscription.';


COMMENT ON COLUMN public.commercialsubscription.purchaser IS 'The person who purchased this subscription.';


COMMENT ON COLUMN public.commercialsubscription.whiteboard IS 'A place for administrators to store comments related to this subscription.';


COMMENT ON COLUMN public.commercialsubscription.sales_system_id IS 'A reference in the external sales system (e.g. Salesforce) that can be used to identify this subscription.';


CREATE SEQUENCE public.commercialsubscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.commercialsubscription_id_seq OWNED BY public.commercialsubscription.id;


CREATE TABLE public.component (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.component IS 'Known components in Launchpad';


COMMENT ON COLUMN public.component.name IS 'Component name text';


COMMENT ON COLUMN public.component.description IS 'Description of this component.';


CREATE SEQUENCE public.component_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.component_id_seq OWNED BY public.component.id;


CREATE TABLE public.componentselection (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    component integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.componentselection IS 'Allowed components in a given distroseries.';


COMMENT ON COLUMN public.componentselection.distroseries IS 'Refers to the distroseries in question.';


COMMENT ON COLUMN public.componentselection.component IS 'Refers to the component in qestion.';


CREATE SEQUENCE public.componentselection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.componentselection_id_seq OWNED BY public.componentselection.id;


CREATE TABLE public.continent (
    id integer NOT NULL,
    code text NOT NULL,
    name text NOT NULL
)
WITH (fillfactor='100');


COMMENT ON TABLE public.continent IS 'A continent in this huge world.';


COMMENT ON COLUMN public.continent.code IS 'A two-letter code for a continent.';


COMMENT ON COLUMN public.continent.name IS 'The name of the continent.';


CREATE SEQUENCE public.continent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.continent_id_seq OWNED BY public.continent.id;


CREATE TABLE public.country (
    id integer NOT NULL,
    iso3166code2 character(2) NOT NULL,
    iso3166code3 character(3) NOT NULL,
    name text NOT NULL,
    title text,
    description text,
    continent integer NOT NULL
)
WITH (fillfactor='100');


CREATE SEQUENCE public.country_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.country_id_seq OWNED BY public.country.id;


CREATE TABLE public.customlanguagecode (
    id integer NOT NULL,
    product integer,
    distribution integer,
    sourcepackagename integer,
    language_code text NOT NULL,
    language integer,
    CONSTRAINT distro_and_sourcepackage CHECK (((sourcepackagename IS NULL) = (distribution IS NULL))),
    CONSTRAINT product_or_distro CHECK (((product IS NULL) <> (distribution IS NULL)))
);


COMMENT ON TABLE public.customlanguagecode IS 'Overrides translation importer''s interpretation of language codes where needed.';


COMMENT ON COLUMN public.customlanguagecode.product IS 'Product for which this custom language code applies (alternative to distribution + source package name).';


COMMENT ON COLUMN public.customlanguagecode.distribution IS 'Distribution in which this custom language code applies (if not a product).';


COMMENT ON COLUMN public.customlanguagecode.sourcepackagename IS 'Source package name to which this custom language code applies; goes with distribution.';


COMMENT ON COLUMN public.customlanguagecode.language_code IS 'Custom language code; need not be for a real language, and typically not for a "useful" language.';


COMMENT ON COLUMN public.customlanguagecode.language IS 'Language to which code really refers in this context, or NULL if files with this code are to be rejected.';


CREATE SEQUENCE public.customlanguagecode_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.customlanguagecode_id_seq OWNED BY public.customlanguagecode.id;


CREATE TABLE public.cve (
    id integer NOT NULL,
    sequence text NOT NULL,
    status integer NOT NULL,
    description text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datemodified timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    fti public.ts2_tsvector,
    CONSTRAINT valid_cve_ref CHECK (public.valid_cve(sequence))
);


COMMENT ON TABLE public.cve IS 'A CVE Entry. The formal database of CVE entries is available at http://cve.mitre.org/ and we sync that database into Launchpad on a regular basis.';


COMMENT ON COLUMN public.cve.sequence IS 'The official CVE entry number. It takes the form XXXX-XXXX where the first four digits are a year indicator, like 2004, and the latter four are the sequence number of the vulnerability in that year.';


COMMENT ON COLUMN public.cve.status IS 'The current status of the CVE. The values are documented in dbschema.CVEState, and are Entry, Candidate, and Deprecated.';


COMMENT ON COLUMN public.cve.datemodified IS 'The last time this CVE entry changed in some way - including addition or modification of references.';


CREATE SEQUENCE public.cve_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cve_id_seq OWNED BY public.cve.id;


CREATE TABLE public.cvereference (
    id integer NOT NULL,
    cve integer NOT NULL,
    source text NOT NULL,
    content text NOT NULL,
    url text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.cvereference IS 'A reference in the CVE system that shows what outside tracking numbers are associated with the CVE. These are tracked in the CVE database and extracted from the daily XML dump that we fetch.';


COMMENT ON COLUMN public.cvereference.source IS 'The SOURCE of the CVE reference. This is a text string, like XF or BUGTRAQ or MSKB. Each string indicates a different kind of reference. The list of known types is documented on the CVE web site. At some future date we might turn this into an enum rather than a text, but for the moment we prefer to keep it fluid and just suck in what CVE gives us. This means that CVE can add new source types without us having to update our code.';


COMMENT ON COLUMN public.cvereference.content IS 'The content of the ref in the CVE database. This is sometimes a comment, sometimes a description, sometimes a bug number... it is not predictable.';


COMMENT ON COLUMN public.cvereference.url IS 'The URL to this reference out there on the web, if it was present in the CVE database.';


CREATE SEQUENCE public.cvereference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cvereference_id_seq OWNED BY public.cvereference.id;


CREATE TABLE public.databasecpustats (
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    username text NOT NULL,
    cpu integer NOT NULL
)
WITH (fillfactor='100');


COMMENT ON TABLE public.databasecpustats IS 'Snapshots of CPU utilization per database username.';


COMMENT ON COLUMN public.databasecpustats.cpu IS '% CPU utilization * 100, as reported by ps -o cp';


CREATE TABLE public.databasediskutilization (
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    namespace text NOT NULL,
    name text NOT NULL,
    sub_namespace text,
    sub_name text,
    kind character(1) NOT NULL,
    sort text NOT NULL,
    table_len bigint NOT NULL,
    tuple_count bigint NOT NULL,
    tuple_len bigint NOT NULL,
    tuple_percent double precision NOT NULL,
    dead_tuple_count bigint NOT NULL,
    dead_tuple_len bigint NOT NULL,
    dead_tuple_percent double precision NOT NULL,
    free_space bigint NOT NULL,
    free_percent double precision NOT NULL
)
WITH (fillfactor='100');


CREATE TABLE public.databasereplicationlag (
    node integer NOT NULL,
    lag interval NOT NULL,
    updated timestamp without time zone DEFAULT timezone('UTC'::text, now())
);


COMMENT ON TABLE public.databasereplicationlag IS 'A cached snapshot of database replication lag between our master Slony node and its slaves.';


COMMENT ON COLUMN public.databasereplicationlag.node IS 'The Slony node number identifying the slave database.';


COMMENT ON COLUMN public.databasereplicationlag.lag IS 'lag time.';


COMMENT ON COLUMN public.databasereplicationlag.updated IS 'When this value was updated.';


CREATE TABLE public.databasetablestats (
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    schemaname name NOT NULL,
    relname name NOT NULL,
    seq_scan bigint NOT NULL,
    seq_tup_read bigint NOT NULL,
    idx_scan bigint NOT NULL,
    idx_tup_fetch bigint NOT NULL,
    n_tup_ins bigint NOT NULL,
    n_tup_upd bigint NOT NULL,
    n_tup_del bigint NOT NULL,
    n_tup_hot_upd bigint NOT NULL,
    n_live_tup bigint NOT NULL,
    n_dead_tup bigint NOT NULL,
    last_vacuum timestamp with time zone,
    last_autovacuum timestamp with time zone,
    last_analyze timestamp with time zone,
    last_autoanalyze timestamp with time zone
)
WITH (fillfactor='100');


COMMENT ON TABLE public.databasetablestats IS 'Snapshots of pg_stat_user_tables to let us calculate arbitrary deltas';


CREATE TABLE public.diff (
    id integer NOT NULL,
    diff_text integer,
    diff_lines_count integer,
    diffstat text,
    added_lines_count integer,
    removed_lines_count integer
);


COMMENT ON TABLE public.diff IS 'Information common to static or preview diffs';


COMMENT ON COLUMN public.diff.diff_text IS 'The library copy of the fulltext of the diff';


COMMENT ON COLUMN public.diff.diff_lines_count IS 'The number of lines in the diff';


COMMENT ON COLUMN public.diff.diffstat IS 'Statistics about the diff';


COMMENT ON COLUMN public.diff.added_lines_count IS 'The number of lines added in the diff.';


COMMENT ON COLUMN public.diff.removed_lines_count IS 'The number of lines removed in the diff';


CREATE SEQUENCE public.diff_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.diff_id_seq OWNED BY public.diff.id;


CREATE TABLE public.distribution (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    domainname text NOT NULL,
    owner integer NOT NULL,
    displayname text NOT NULL,
    summary text NOT NULL,
    members integer NOT NULL,
    translationgroup integer,
    translationpermission integer DEFAULT 1 NOT NULL,
    bug_supervisor integer,
    official_malone boolean DEFAULT false NOT NULL,
    official_rosetta boolean DEFAULT false NOT NULL,
    driver integer,
    translation_focus integer,
    mirror_admin integer NOT NULL,
    upload_sender text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    homepage_content text,
    icon integer,
    mugshot integer,
    logo integer,
    fti public.ts2_tsvector,
    official_answers boolean DEFAULT false NOT NULL,
    language_pack_admin integer,
    official_blueprints boolean DEFAULT false NOT NULL,
    enable_bug_expiration boolean DEFAULT false NOT NULL,
    bug_reporting_guidelines text,
    reviewer_whiteboard text,
    max_bug_heat integer,
    bug_reported_acknowledgement text,
    answers_usage integer DEFAULT 10 NOT NULL,
    blueprints_usage integer DEFAULT 10 NOT NULL,
    translations_usage integer DEFAULT 10 NOT NULL,
    registrant integer NOT NULL,
    package_derivatives_email text,
    redirect_release_uploads boolean DEFAULT false NOT NULL,
    development_series_alias text,
    official_packages boolean DEFAULT false NOT NULL,
    supports_ppas boolean DEFAULT false NOT NULL,
    supports_mirrors boolean DEFAULT false NOT NULL,
    vcs integer,
    CONSTRAINT only_launchpad_has_expiration CHECK (((enable_bug_expiration IS FALSE) OR (official_malone IS TRUE))),
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.distribution IS 'Distribution: A soyuz distribution. A distribution is a collection of DistroSeries. Distributions often group together policy and may be referred to by a name such as "Ubuntu" or "Debian"';


COMMENT ON COLUMN public.distribution.name IS 'The unique name of the distribution as a short lowercase name suitable for use in a URL.';


COMMENT ON COLUMN public.distribution.title IS 'The title of the distribution. More a "display name" as it were. E.g. "Ubuntu" or "Debian GNU/Linux"';


COMMENT ON COLUMN public.distribution.description IS 'A description of the distribution. More detailed than the title, this column may also contain information about the project this distribution is run by.';


COMMENT ON COLUMN public.distribution.domainname IS 'The domain name of the distribution. This may be used both for linking to the distribution and for context-related stuff.';


COMMENT ON COLUMN public.distribution.owner IS 'The person in launchpad who is in ultimate-charge of this distribution within launchpad.';


COMMENT ON COLUMN public.distribution.displayname IS 'A short, well-capitalised
name for this distribution that is not required to be unique but in almost
all cases would be so.';


COMMENT ON COLUMN public.distribution.summary IS 'A single paragraph that
summarises the highlights of this distribution. It should be no longer than
240 characters, although this is not enforced in the database.';


COMMENT ON COLUMN public.distribution.members IS 'Person or team with upload and commit priviledges relating to this distribution. Other rights may be assigned to this role in the future.';


COMMENT ON COLUMN public.distribution.translationgroup IS 'The translation group that is responsible for all translation work in this distribution.';


COMMENT ON COLUMN public.distribution.translationpermission IS 'The level of openness of this distribution''s translation process. The enum lists different approaches to translation, from the very open (anybody can edit any translation in any language) to the completely closed (only designated translators can make any changes at all).';


COMMENT ON COLUMN public.distribution.bug_supervisor IS 'Person who is responsible for managing bugs on this distribution.';


COMMENT ON COLUMN public.distribution.official_malone IS 'Whether or not this distribution uses Malone for an official bug tracker.';


COMMENT ON COLUMN public.distribution.official_rosetta IS 'Whether or not this distribution uses Rosetta for its official translation team and coordination.';


COMMENT ON COLUMN public.distribution.driver IS 'The team or person responsible for approving goals for each release in the distribution. This should usually be a very small team because the Distribution driver can approve items for backporting to past releases as well as the current release under development. Each distroseries has its own driver too, so you can have the small superset in the Distribution driver, and then specific teams per distroseries for backporting, for example, or for the current release management team on the current development focus release.';


COMMENT ON COLUMN public.distribution.translation_focus IS 'The DistroSeries that should get the translation effort focus.';


COMMENT ON COLUMN public.distribution.mirror_admin IS 'Person or team with privileges to mark a mirror as official.';


COMMENT ON COLUMN public.distribution.upload_sender IS 'The email address (and name) of the default sender used by the upload processor. If NULL, we fall back to the default sender in the launchpad config.';


COMMENT ON COLUMN public.distribution.homepage_content IS 'A home page for this distribution in the Launchpad.';


COMMENT ON COLUMN public.distribution.icon IS 'The library file alias to a small image to be used as an icon whenever we are referring to a distribution.';


COMMENT ON COLUMN public.distribution.mugshot IS 'The library file alias of a mugshot image to display as the branding of a distribution, on its home page.';


COMMENT ON COLUMN public.distribution.logo IS 'The library file alias of a smaller version of this distributions''s mugshot.';


COMMENT ON COLUMN public.distribution.official_answers IS 'Whether or not this product upstream uses Answers officialy.';


COMMENT ON COLUMN public.distribution.language_pack_admin IS 'The Person or Team that handle language packs for the distro release.';


COMMENT ON COLUMN public.distribution.enable_bug_expiration IS 'Indicates whether automatic bug expiration is enabled.';


COMMENT ON COLUMN public.distribution.bug_reporting_guidelines IS 'Guidelines to the end user for reporting bugs on this distribution.';


COMMENT ON COLUMN public.distribution.reviewer_whiteboard IS 'A whiteboard for Launchpad admins, registry experts and the project owners to capture the state of current issues with the project.';


COMMENT ON COLUMN public.distribution.max_bug_heat IS 'The highest heat value across bugs for this distribution.';


COMMENT ON COLUMN public.distribution.bug_reported_acknowledgement IS 'A message of acknowledgement to display to a bug reporter after they''ve reported a new bug.';


COMMENT ON COLUMN public.distribution.registrant IS 'The person in launchpad who registered this distribution.';


COMMENT ON COLUMN public.distribution.package_derivatives_email IS 'The optional email address template to use when sending emails about package updates in a distributrion. The string {package_name} in the template will be replaced with the actual package name being updated.';


COMMENT ON COLUMN public.distribution.redirect_release_uploads IS 'Whether uploads to the release pocket of this distribution should be redirected to the proposed pocket instead.';


COMMENT ON COLUMN public.distribution.development_series_alias IS 'If set, an alias for the current development series in this distribution.';


COMMENT ON COLUMN public.distribution.vcs IS 'An enumeration specifying the default version control system for this distribution.';


CREATE SEQUENCE public.distribution_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distribution_id_seq OWNED BY public.distribution.id;


CREATE TABLE public.distributionjob (
    id integer NOT NULL,
    job integer NOT NULL,
    distribution integer NOT NULL,
    distroseries integer,
    job_type integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.distributionjob IS 'Contains references to jobs to be run on distributions.';


COMMENT ON COLUMN public.distributionjob.distribution IS 'The distribution to be acted on.';


COMMENT ON COLUMN public.distributionjob.distroseries IS 'The distroseries to be acted on.';


COMMENT ON COLUMN public.distributionjob.job_type IS 'The type of job';


COMMENT ON COLUMN public.distributionjob.json_data IS 'A JSON struct containing data for the job.';


CREATE SEQUENCE public.distributionjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distributionjob_id_seq OWNED BY public.distributionjob.id;


CREATE TABLE public.distributionmirror (
    id integer NOT NULL,
    distribution integer NOT NULL,
    name text NOT NULL,
    http_base_url text,
    ftp_base_url text,
    rsync_base_url text,
    displayname text,
    description text,
    owner integer NOT NULL,
    speed integer NOT NULL,
    country integer NOT NULL,
    content integer NOT NULL,
    official_candidate boolean DEFAULT false NOT NULL,
    enabled boolean DEFAULT false NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    whiteboard text,
    status integer DEFAULT 10 NOT NULL,
    date_reviewed timestamp without time zone,
    reviewer integer,
    country_dns_mirror boolean DEFAULT false NOT NULL,
    CONSTRAINT one_or_more_urls CHECK ((((http_base_url IS NOT NULL) OR (ftp_base_url IS NOT NULL)) OR (rsync_base_url IS NOT NULL))),
    CONSTRAINT valid_ftp_base_url CHECK (public.valid_absolute_url(ftp_base_url)),
    CONSTRAINT valid_http_base_url CHECK (public.valid_absolute_url(http_base_url)),
    CONSTRAINT valid_name CHECK (public.valid_name(name)),
    CONSTRAINT valid_rsync_base_url CHECK (public.valid_absolute_url(rsync_base_url))
);


COMMENT ON TABLE public.distributionmirror IS 'A mirror of a given distribution.';


COMMENT ON COLUMN public.distributionmirror.distribution IS 'The distribution to which the mirror refers to.';


COMMENT ON COLUMN public.distributionmirror.name IS 'The unique name of the mirror.';


COMMENT ON COLUMN public.distributionmirror.http_base_url IS 'The HTTP URL used to access the mirror.';


COMMENT ON COLUMN public.distributionmirror.ftp_base_url IS 'The FTP URL used to access the mirror.';


COMMENT ON COLUMN public.distributionmirror.rsync_base_url IS 'The Rsync URL used to access the mirror.';


COMMENT ON COLUMN public.distributionmirror.displayname IS 'The displayname of the mirror.';


COMMENT ON COLUMN public.distributionmirror.description IS 'A description of the mirror.';


COMMENT ON COLUMN public.distributionmirror.owner IS 'The owner of the mirror.';


COMMENT ON COLUMN public.distributionmirror.speed IS 'The speed of the mirror''s Internet link.';


COMMENT ON COLUMN public.distributionmirror.country IS 'The country where the mirror is located.';


COMMENT ON COLUMN public.distributionmirror.content IS 'The content that is mirrored.';


COMMENT ON COLUMN public.distributionmirror.official_candidate IS 'Is the mirror a candidate for becoming an official mirror?';


COMMENT ON COLUMN public.distributionmirror.enabled IS 'Is this mirror enabled?';


COMMENT ON COLUMN public.distributionmirror.date_created IS 'The date and time the mirror was created.';


COMMENT ON COLUMN public.distributionmirror.whiteboard IS 'Notes on the current status of the mirror';


COMMENT ON COLUMN public.distributionmirror.status IS 'This mirror''s status.';


COMMENT ON COLUMN public.distributionmirror.date_reviewed IS 'The date and time the mirror was reviewed.';


COMMENT ON COLUMN public.distributionmirror.reviewer IS 'The person who reviewed the mirror.';


COMMENT ON COLUMN public.distributionmirror.country_dns_mirror IS 'Is the mirror a country DNS mirror?';


CREATE SEQUENCE public.distributionmirror_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distributionmirror_id_seq OWNED BY public.distributionmirror.id;


CREATE TABLE public.distributionsourcepackage (
    id integer NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    bug_reporting_guidelines text,
    max_bug_heat integer,
    bug_reported_acknowledgement text,
    total_bug_heat integer,
    bug_count integer,
    po_message_count integer,
    is_upstream_link_allowed boolean DEFAULT true NOT NULL,
    enable_bugfiling_duplicate_search boolean DEFAULT true NOT NULL
);


COMMENT ON TABLE public.distributionsourcepackage IS 'Representing a sourcepackage in a distribution across all distribution series.';


COMMENT ON COLUMN public.distributionsourcepackage.bug_reporting_guidelines IS 'Guidelines to the end user for reporting bugs on a particular a source package in a distribution.';


COMMENT ON COLUMN public.distributionsourcepackage.max_bug_heat IS 'The highest heat value across bugs for this source package. NULL means it has not yet been calculated.';


COMMENT ON COLUMN public.distributionsourcepackage.bug_reported_acknowledgement IS 'A message of acknowledgement to display to a bug reporter after they''ve reported a new bug.';


COMMENT ON COLUMN public.distributionsourcepackage.total_bug_heat IS 'Sum of bug heat matching the package distribution and sourcepackagename. NULL means it has not yet been calculated.';


COMMENT ON COLUMN public.distributionsourcepackage.bug_count IS 'Number of bugs matching the package distribution and sourcepackagename. NULL means it has not yet been calculated.';


COMMENT ON COLUMN public.distributionsourcepackage.po_message_count IS 'Number of translations matching the package distribution and sourcepackagename. NULL means it has not yet been calculated.';


COMMENT ON COLUMN public.distributionsourcepackage.is_upstream_link_allowed IS 'Whether an upstream link may be added if it does not already exist.';


COMMENT ON COLUMN public.distributionsourcepackage.enable_bugfiling_duplicate_search IS 'Enable/disable a search for posiible duplicates when a bug is filed.';


CREATE SEQUENCE public.distributionsourcepackage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distributionsourcepackage_id_seq OWNED BY public.distributionsourcepackage.id;


CREATE TABLE public.distributionsourcepackagecache (
    id integer NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    name text,
    binpkgnames text,
    binpkgsummaries text,
    binpkgdescriptions text,
    fti public.ts2_tsvector,
    changelog text,
    archive integer
);


COMMENT ON TABLE public.distributionsourcepackagecache IS 'A cache of the text associated with binary and source packages in the distribution. This table allows for fast queries to find a source packagename that matches a given text.';


COMMENT ON COLUMN public.distributionsourcepackagecache.distribution IS 'The distribution in which we are checking.';


COMMENT ON COLUMN public.distributionsourcepackagecache.sourcepackagename IS 'The source package name for which we are caching details.';


COMMENT ON COLUMN public.distributionsourcepackagecache.name IS 'The source package name itself. This is just a copy of the value of sourcepackagename.name. We have it here so it can be part of the full text index.';


COMMENT ON COLUMN public.distributionsourcepackagecache.binpkgnames IS 'The binary package names of binary packages generated from these source packages across all architectures.';


COMMENT ON COLUMN public.distributionsourcepackagecache.binpkgsummaries IS 'The aggregated summaries of all the binary packages generated from these source packages in this distribution.';


COMMENT ON COLUMN public.distributionsourcepackagecache.binpkgdescriptions IS 'The aggregated description of all the binary packages generated from these source packages in this distribution.';


COMMENT ON COLUMN public.distributionsourcepackagecache.changelog IS 'A concatenation of the source package release changelogs for this source package, where the status is not REMOVED.';


COMMENT ON COLUMN public.distributionsourcepackagecache.archive IS 'The archive where the source is published.';


CREATE SEQUENCE public.distributionsourcepackagecache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distributionsourcepackagecache_id_seq OWNED BY public.distributionsourcepackagecache.id;


CREATE TABLE public.distroarchseries (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    architecturetag text NOT NULL,
    owner integer NOT NULL,
    official boolean NOT NULL,
    package_count integer DEFAULT 0 NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    processor integer NOT NULL,
    CONSTRAINT valid_architecturetag CHECK (public.valid_name(architecturetag))
);


COMMENT ON TABLE public.distroarchseries IS 'DistroArchSeries: A soyuz distribution release for a given architecture. A distroseries runs on various architectures. The distroarchseries groups that architecture-specific stuff.';


COMMENT ON COLUMN public.distroarchseries.distroseries IS 'The distribution which this distroarchseries is part of.';


COMMENT ON COLUMN public.distroarchseries.architecturetag IS 'The name of this architecture in the context of this specific distro release. For example, some distributions might label amd64 as amd64, others might call is x86_64. This information is used, for example, in determining the names of the actual package files... such as the "amd64" part of "apache2_2.0.56-1_amd64.deb"';


COMMENT ON COLUMN public.distroarchseries.official IS 'Whether or not this architecture or "port" is an official release. If it is not official then you may not be able to install it or get all the packages for it.';


COMMENT ON COLUMN public.distroarchseries.package_count IS 'A cache of the number of binary packages published in this distro arch release. The count only includes packages published in the release pocket.';


COMMENT ON COLUMN public.distroarchseries.enabled IS 'Whether to allow build creation and publishing for this DistroArchSeries.';


COMMENT ON COLUMN public.distroarchseries.processor IS 'A link to the Processor table, giving the architecture of this DistroArchSeries.';


CREATE SEQUENCE public.distroarchseries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distroarchseries_id_seq OWNED BY public.distroarchseries.id;


CREATE TABLE public.distroseries (
    id integer NOT NULL,
    distribution integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    version text NOT NULL,
    releasestatus integer NOT NULL,
    datereleased timestamp without time zone,
    parent_series integer,
    registrant integer NOT NULL,
    summary text NOT NULL,
    displayname text NOT NULL,
    datelastlangpack timestamp without time zone,
    messagecount integer DEFAULT 0 NOT NULL,
    nominatedarchindep integer,
    changeslist text,
    binarycount integer DEFAULT 0 NOT NULL,
    sourcecount integer DEFAULT 0 NOT NULL,
    driver integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    hide_all_translations boolean DEFAULT true NOT NULL,
    defer_translation_imports boolean DEFAULT true NOT NULL,
    language_pack_base integer,
    language_pack_delta integer,
    language_pack_proposed integer,
    language_pack_full_export_requested boolean DEFAULT false NOT NULL,
    backports_not_automatic boolean DEFAULT false NOT NULL,
    include_long_descriptions boolean DEFAULT true NOT NULL,
    proposed_not_automatic boolean DEFAULT false NOT NULL,
    publishing_options text,
    CONSTRAINT valid_language_pack_delta CHECK (((language_pack_base IS NOT NULL) OR (language_pack_delta IS NULL))),
    CONSTRAINT valid_name CHECK (public.valid_name(name)),
    CONSTRAINT valid_version CHECK (public.sane_version(version))
);


COMMENT ON TABLE public.distroseries IS 'DistroSeries: A soyuz distribution release. A DistroSeries is a given version of a distribution. E.g. "Warty" "Hoary" "Sarge" etc.';


COMMENT ON COLUMN public.distroseries.distribution IS 'The distribution which contains this distroseries.';


COMMENT ON COLUMN public.distroseries.name IS 'The unique name of the distroseries. This is a short name in lower case and would be used in sources.list configuration and in generated URLs. E.g. "warty" "sarge" "sid"';


COMMENT ON COLUMN public.distroseries.title IS 'The display-name title of the distroseries E.g. "Warty Warthog"';


COMMENT ON COLUMN public.distroseries.description IS 'The long detailed description of the release. This may describe the focus of the release or other related information.';


COMMENT ON COLUMN public.distroseries.version IS 'The version of the release. E.g. warty would be "4.10" and hoary would be "5.4"';


COMMENT ON COLUMN public.distroseries.releasestatus IS 'The current release status of this distroseries. E.g. "pre-release freeze" or "released"';


COMMENT ON COLUMN public.distroseries.datereleased IS 'The date on which this distroseries was released. (obviously only valid for released distributions)';


COMMENT ON COLUMN public.distroseries.parent_series IS 'The parent distroseries on which this distribution is based. This is related to the inheritance stuff.';


COMMENT ON COLUMN public.distroseries.registrant IS 'The user who registered this distroseries.';


COMMENT ON COLUMN public.distroseries.summary IS 'A brief summary of the distro release. This will be displayed in bold at the top of the distroseries page, above the distroseries description. It should include any high points that are particularly important to draw to the attention of users.';


COMMENT ON COLUMN public.distroseries.datelastlangpack IS 'The date we last generated a base language pack for this release. Language update packs for this release will only include translations added after that date.';


COMMENT ON COLUMN public.distroseries.messagecount IS 'This is a cached value and may be a few hours out of sync with reality. It should, however, be in sync with the values in DistroSeriesLanguage, and should never be updated separately. The total number of translation messages in this distro release, as per IRosettaStats.';


COMMENT ON COLUMN public.distroseries.nominatedarchindep IS 'This is the DistroArchSeries nominated to build architecture independent packages within this DistroRelase, it is mandatory for buildable distroseries, i.e., Auto Build System will avoid to create build jobs for a DistroSeries with no nominatedarchindep, but the database model allow us to do it (for non-buildable DistroSeries). See further info in NominatedArchIndep specification.';


COMMENT ON COLUMN public.distroseries.changeslist IS 'The email address (name name) of the changes announcement list for this distroseries. If NULL, no announcement mail will be sent.';


COMMENT ON COLUMN public.distroseries.binarycount IS 'A cache of the number of distinct binary package names published in this distro release.';


COMMENT ON COLUMN public.distroseries.sourcecount IS 'A cache of the number of distinct source package names published in this distro release.';


COMMENT ON COLUMN public.distroseries.driver IS 'This is a person or team who can act as a driver for this specific release - note that the distribution drivers can also set goals for any release.';


COMMENT ON COLUMN public.distroseries.hide_all_translations IS 'Whether we should hid
e all available translations for this distro release to non admin users.';


COMMENT ON COLUMN public.distroseries.defer_translation_imports IS 'Don''t accept PO imports for this release just now.';


COMMENT ON COLUMN public.distroseries.language_pack_base IS 'Current full export language pack for this distribution release.';


COMMENT ON COLUMN public.distroseries.language_pack_delta IS 'Current language pack update based on language_pack_base information.';


COMMENT ON COLUMN public.distroseries.language_pack_proposed IS 'Either a full or update language pack being tested to be used in language_pack_base or language_pack_delta.';


COMMENT ON COLUMN public.distroseries.language_pack_full_export_requested IS 'Whether next language pack export should be a full export or an update.';


COMMENT ON COLUMN public.distroseries.include_long_descriptions IS 'Include long descriptions in Packages rather than in Translation-en.';


COMMENT ON COLUMN public.distroseries.proposed_not_automatic IS 'Whether the -proposed pocket is set NotAutomatic and ButAutomaticUpgrades so that apt does not offer users upgrades into -proposed, but does offer upgrades within it.';


COMMENT ON COLUMN public.distroseries.publishing_options IS 'A JSON object containing options modifying the publisher''s behaviour for this series.';


CREATE SEQUENCE public.distroseries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distroseries_id_seq OWNED BY public.distroseries.id;


CREATE TABLE public.distroseriesdifference (
    id integer NOT NULL,
    derived_series integer NOT NULL,
    source_package_name integer NOT NULL,
    package_diff integer,
    status integer NOT NULL,
    difference_type integer NOT NULL,
    parent_package_diff integer,
    source_version public.debversion,
    parent_source_version public.debversion,
    base_version public.debversion,
    parent_series integer NOT NULL,
    CONSTRAINT valid_base_version CHECK (public.valid_debian_version((base_version)::text)),
    CONSTRAINT valid_parent_source_version CHECK (public.valid_debian_version((parent_source_version)::text)),
    CONSTRAINT valid_source_version CHECK (public.valid_debian_version((source_version)::text))
);


COMMENT ON TABLE public.distroseriesdifference IS 'A difference of versions for a package in a derived distroseries and its parent distroseries.';


COMMENT ON COLUMN public.distroseriesdifference.derived_series IS 'The derived distroseries with the difference from its parent.';


COMMENT ON COLUMN public.distroseriesdifference.source_package_name IS 'The name of the source package which is different in the two series.';


COMMENT ON COLUMN public.distroseriesdifference.package_diff IS 'The most recent package diff that was created for the base version to derived version.';


COMMENT ON COLUMN public.distroseriesdifference.status IS 'A distroseries difference can be needing attention, ignored or resolved.';


COMMENT ON COLUMN public.distroseriesdifference.difference_type IS 'The type of difference that this record represents - a package unique to the derived series, or missing, or in both.';


COMMENT ON COLUMN public.distroseriesdifference.parent_package_diff IS 'The most recent package diff that was created for the base version to the parent version.';


COMMENT ON COLUMN public.distroseriesdifference.source_version IS 'The version of the package in the derived series.';


COMMENT ON COLUMN public.distroseriesdifference.parent_source_version IS 'The version of the package in the parent series.';


COMMENT ON COLUMN public.distroseriesdifference.base_version IS 'The common base version of the package for the derived and parent series.';


COMMENT ON COLUMN public.distroseriesdifference.parent_series IS 'The parent distroseries with the difference from its child.';


CREATE SEQUENCE public.distroseriesdifference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distroseriesdifference_id_seq OWNED BY public.distroseriesdifference.id;


CREATE TABLE public.distroseriesdifferencemessage (
    id integer NOT NULL,
    distro_series_difference integer NOT NULL,
    message integer NOT NULL
);


COMMENT ON TABLE public.distroseriesdifferencemessage IS 'A message/comment on a distro series difference.';


COMMENT ON COLUMN public.distroseriesdifferencemessage.distro_series_difference IS 'The distro series difference for this comment.';


COMMENT ON COLUMN public.distroseriesdifferencemessage.message IS 'The comment for the distro series difference.';


CREATE SEQUENCE public.distroseriesdifferencemessage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distroseriesdifferencemessage_id_seq OWNED BY public.distroseriesdifferencemessage.id;


CREATE TABLE public.distroserieslanguage (
    id integer NOT NULL,
    distroseries integer,
    language integer,
    currentcount integer NOT NULL,
    updatescount integer NOT NULL,
    rosettacount integer NOT NULL,
    contributorcount integer NOT NULL,
    dateupdated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    unreviewed_count integer DEFAULT 0 NOT NULL
);


COMMENT ON TABLE public.distroserieslanguage IS 'A cache of the current translation status of that language across an entire distroseries.';


COMMENT ON COLUMN public.distroserieslanguage.currentcount IS 'As per IRosettaStats.';


COMMENT ON COLUMN public.distroserieslanguage.updatescount IS 'As per IRosettaStats.';


COMMENT ON COLUMN public.distroserieslanguage.rosettacount IS 'As per IRosettaStats.';


COMMENT ON COLUMN public.distroserieslanguage.contributorcount IS 'The total number of contributors to the translation of this distroseries into this language.';


COMMENT ON COLUMN public.distroserieslanguage.dateupdated IS 'The date these statistucs were last updated.';


COMMENT ON COLUMN public.distroserieslanguage.unreviewed_count IS 'As per IRosettaStats.';


CREATE SEQUENCE public.distroserieslanguage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distroserieslanguage_id_seq OWNED BY public.distroserieslanguage.id;


CREATE TABLE public.distroseriespackagecache (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    binarypackagename integer NOT NULL,
    name text,
    summary text,
    description text,
    summaries text,
    descriptions text,
    fti public.ts2_tsvector,
    archive integer NOT NULL
);


COMMENT ON TABLE public.distroseriespackagecache IS 'A cache of the text associated with binary packages in the distroseries. This table allows for fast queries to find a binary packagename that matches a given text.';


COMMENT ON COLUMN public.distroseriespackagecache.distroseries IS 'The distroseries in which we are checking.';


COMMENT ON COLUMN public.distroseriespackagecache.binarypackagename IS 'The binary package name for which we are caching details.';


COMMENT ON COLUMN public.distroseriespackagecache.name IS 'The binary package name itself. This is just a copy of the value of binarypackagename.name. We have it here so it can be part of the full text index.';


COMMENT ON COLUMN public.distroseriespackagecache.summary IS 'A single summary for one of the binary packages of this name in this distroseries. We could potentially have binary packages in different architectures with the same name and different summaries, so this is a way of collapsing to one arbitrarily-chosen one, for display purposes. The chances of actually having different summaries and descriptions is pretty small. It could happen, though, because of the way package superseding works when a package does not build on a specific architecture.';


COMMENT ON COLUMN public.distroseriespackagecache.summaries IS 'The aggregated summaries of all the binary packages with this name in this distroseries.';


COMMENT ON COLUMN public.distroseriespackagecache.descriptions IS 'The aggregated description of all the binary packages with this name in this distroseries.';


COMMENT ON COLUMN public.distroseriespackagecache.archive IS 'The archive where the binary is published.';


CREATE SEQUENCE public.distroseriespackagecache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distroseriespackagecache_id_seq OWNED BY public.distroseriespackagecache.id;


CREATE TABLE public.distroseriesparent (
    id integer NOT NULL,
    derived_series integer NOT NULL,
    parent_series integer NOT NULL,
    initialized boolean NOT NULL,
    is_overlay boolean DEFAULT false NOT NULL,
    component integer,
    pocket integer,
    ordering integer DEFAULT 1 NOT NULL,
    inherit_overrides boolean DEFAULT false NOT NULL
);


COMMENT ON TABLE public.distroseriesparent IS 'A list of all the derived distroseries for a parent series.';


COMMENT ON COLUMN public.distroseriesparent.derived_series IS 'The derived distroseries';


COMMENT ON COLUMN public.distroseriesparent.parent_series IS 'The parent distroseries';


COMMENT ON COLUMN public.distroseriesparent.initialized IS 'Whether or not the derived series was initialized by copying packages from the parent.';


COMMENT ON COLUMN public.distroseriesparent.is_overlay IS 'Whether or not the derived series is an overlay over the parent series.';


COMMENT ON COLUMN public.distroseriesparent.component IS 'The component for this overlay.';


COMMENT ON COLUMN public.distroseriesparent.pocket IS 'The pocket for this overlay.';


COMMENT ON COLUMN public.distroseriesparent.ordering IS 'The parent ordering. Parents are ordered in ascending order starting from 1.';


CREATE SEQUENCE public.distroseriesparent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distroseriesparent_id_seq OWNED BY public.distroseriesparent.id;


CREATE TABLE public.emailaddress (
    id integer NOT NULL,
    email text NOT NULL,
    person integer NOT NULL,
    status integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON COLUMN public.emailaddress.email IS 'An email address used by a Person. The email address is stored in a casesensitive way, but must be case insensitivly unique.';


CREATE SEQUENCE public.emailaddress_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.emailaddress_id_seq OWNED BY public.emailaddress.id;


CREATE TABLE public.faq (
    id integer NOT NULL,
    title text NOT NULL,
    tags text,
    content text NOT NULL,
    product integer,
    distribution integer,
    owner integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    last_updated_by integer,
    date_last_updated timestamp without time zone,
    fti public.ts2_tsvector,
    CONSTRAINT product_or_distro CHECK (((product IS NULL) <> (distribution IS NULL)))
);


COMMENT ON TABLE public.faq IS 'A technical document containing the answer to a common question.';


COMMENT ON COLUMN public.faq.id IS 'The FAQ document sequence number.';


COMMENT ON COLUMN public.faq.title IS 'The document title.';


COMMENT ON COLUMN public.faq.tags IS 'White-space separated list of tags.';


COMMENT ON COLUMN public.faq.content IS 'The content of FAQ. It can also contain a short summary and a link.';


COMMENT ON COLUMN public.faq.product IS 'The product to which this document is
related. Either "product" or "distribution" must be set.';


COMMENT ON COLUMN public.faq.distribution IS 'The distribution to which this document
is related. Either "product" or "distribution" must be set.';


COMMENT ON COLUMN public.faq.owner IS 'The person who created the document.';


COMMENT ON COLUMN public.faq.date_created IS 'The datetime when the document was created.';


COMMENT ON COLUMN public.faq.last_updated_by IS 'The person who last modified the document.';


COMMENT ON COLUMN public.faq.date_last_updated IS 'The datetime when the document was last modified.';


CREATE SEQUENCE public.faq_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.faq_id_seq OWNED BY public.faq.id;


CREATE TABLE public.featuredproject (
    id integer NOT NULL,
    pillar_name integer NOT NULL
);


COMMENT ON TABLE public.featuredproject IS 'A list of featured projects. This table is really just a list of pillarname IDs, if a project''s pillar name is in this list then it is a featured project and will be listed on the Launchpad home page.';


COMMENT ON COLUMN public.featuredproject.pillar_name IS 'A reference to PillarName.id';


CREATE SEQUENCE public.featuredproject_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.featuredproject_id_seq OWNED BY public.featuredproject.id;


CREATE TABLE public.featureflag (
    scope text NOT NULL,
    priority integer NOT NULL,
    flag text NOT NULL,
    value text NOT NULL,
    date_modified timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


COMMENT ON TABLE public.featureflag IS 'Configuration that varies by the active scope and that 
can be changed without restarting Launchpad
<https://dev.launchpad.net/LEP/FeatureFlags>';


COMMENT ON COLUMN public.featureflag.scope IS 'Scope in which this setting is active';


COMMENT ON COLUMN public.featureflag.priority IS 'Higher priority flags override lower';


COMMENT ON COLUMN public.featureflag.flag IS 'Name of the flag being controlled';


CREATE TABLE public.featureflagchangelogentry (
    id integer NOT NULL,
    date_changed timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    diff text NOT NULL,
    comment text NOT NULL,
    person integer NOT NULL
);


COMMENT ON TABLE public.featureflagchangelogentry IS 'A record of changes to the FeatureFlag table.';


COMMENT ON COLUMN public.featureflagchangelogentry.date_changed IS 'The timestamp for when the change was made';


COMMENT ON COLUMN public.featureflagchangelogentry.diff IS 'A unified diff of the change.';


COMMENT ON COLUMN public.featureflagchangelogentry.comment IS 'A comment explaining the change.';


COMMENT ON COLUMN public.featureflagchangelogentry.person IS 'The person who made this change.';


CREATE SEQUENCE public.featureflagchangelogentry_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.featureflagchangelogentry_id_seq OWNED BY public.featureflagchangelogentry.id;


CREATE TABLE public.flatpackagesetinclusion (
    id integer NOT NULL,
    parent integer NOT NULL,
    child integer NOT NULL
);


COMMENT ON TABLE public.flatpackagesetinclusion IS 'In order to facilitate the querying of set-subset relationships an expanded or flattened representation of the set-subset hierarchy is provided by this table.';


COMMENT ON COLUMN public.flatpackagesetinclusion.parent IS 'The package set that is (directly or indirectly) including a subset.';


COMMENT ON COLUMN public.flatpackagesetinclusion.child IS 'The package set that is being included as a subset.';


CREATE SEQUENCE public.flatpackagesetinclusion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.flatpackagesetinclusion_id_seq OWNED BY public.flatpackagesetinclusion.id;


CREATE TABLE public.fticache (
    id integer NOT NULL,
    tablename text NOT NULL,
    columns text NOT NULL
);


CREATE SEQUENCE public.fticache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fticache_id_seq OWNED BY public.fticache.id;


CREATE TABLE public.garbojobstate (
    name text NOT NULL,
    json_data text
);


COMMENT ON TABLE public.garbojobstate IS 'Contains persistent state for named garbo jobs.';


COMMENT ON COLUMN public.garbojobstate.name IS 'The name of the job.';


COMMENT ON COLUMN public.garbojobstate.json_data IS 'A JSON struct containing data for the job.';


CREATE TABLE public.gitactivity (
    id integer NOT NULL,
    repository integer NOT NULL,
    date_changed timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    changer integer NOT NULL,
    changee integer,
    what_changed integer NOT NULL,
    old_value text,
    new_value text
);


COMMENT ON TABLE public.gitactivity IS 'An activity log entry for a Git repository.';


COMMENT ON COLUMN public.gitactivity.repository IS 'The repository that this log entry is for.';


COMMENT ON COLUMN public.gitactivity.date_changed IS 'The time when this change happened.';


COMMENT ON COLUMN public.gitactivity.changer IS 'The user who made this change.';


COMMENT ON COLUMN public.gitactivity.changee IS 'The person or team that this change was applied to.';


COMMENT ON COLUMN public.gitactivity.what_changed IS 'The property of the repository that changed.';


COMMENT ON COLUMN public.gitactivity.old_value IS 'JSON object representing the value before the change.';


COMMENT ON COLUMN public.gitactivity.new_value IS 'JSON object representing the value after the change.';


CREATE SEQUENCE public.gitactivity_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gitactivity_id_seq OWNED BY public.gitactivity.id;


CREATE TABLE public.gitjob (
    job integer NOT NULL,
    repository integer,
    job_type integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.gitjob IS 'Contains references to jobs that are executed for a Git repository.';


COMMENT ON COLUMN public.gitjob.job IS 'A reference to a Job row that has all the common job details.';


COMMENT ON COLUMN public.gitjob.repository IS 'The repository that this job is for.';


COMMENT ON COLUMN public.gitjob.job_type IS 'The type of job, such as a ref scan.';


COMMENT ON COLUMN public.gitjob.json_data IS 'Data that is specific to a particular job type.';


CREATE TABLE public.gitref (
    repository integer NOT NULL,
    path text NOT NULL,
    commit_sha1 character(40) NOT NULL,
    object_type integer NOT NULL,
    author integer,
    author_date timestamp without time zone,
    committer integer,
    committer_date timestamp without time zone,
    commit_message text
);


COMMENT ON TABLE public.gitref IS 'A reference in a Git repository.';


COMMENT ON COLUMN public.gitref.repository IS 'The repository containing this reference.';


COMMENT ON COLUMN public.gitref.path IS 'The full path of the reference, e.g. refs/heads/master.';


COMMENT ON COLUMN public.gitref.commit_sha1 IS 'The SHA-1 hash of the object pointed to by this reference.';


COMMENT ON COLUMN public.gitref.object_type IS 'The type of object pointed to by this reference.';


COMMENT ON COLUMN public.gitref.author IS 'The author of the commit pointed to by this reference.';


COMMENT ON COLUMN public.gitref.author_date IS 'The author date of the commit pointed to by this reference.';


COMMENT ON COLUMN public.gitref.committer IS 'The committer of the commit pointed to by this reference.';


COMMENT ON COLUMN public.gitref.committer_date IS 'The committer date of the commit pointed to by this reference.';


COMMENT ON COLUMN public.gitref.commit_message IS 'The commit message of the commit pointed to by this reference.';


CREATE TABLE public.gitrepository (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    owner integer NOT NULL,
    project integer,
    distribution integer,
    sourcepackagename integer,
    name text NOT NULL,
    information_type integer NOT NULL,
    owner_default boolean DEFAULT false NOT NULL,
    target_default boolean DEFAULT false NOT NULL,
    access_policy integer,
    access_grants integer[],
    description text,
    reviewer integer,
    default_branch text,
    repository_type integer NOT NULL,
    CONSTRAINT default_implies_target CHECK ((((project IS NOT NULL) OR (distribution IS NOT NULL)) OR ((NOT owner_default) AND (NOT target_default)))),
    CONSTRAINT one_container CHECK ((((project IS NULL) OR (distribution IS NULL)) AND ((distribution IS NULL) = (sourcepackagename IS NULL)))),
    CONSTRAINT valid_name CHECK (public.valid_git_repository_name(name))
);


COMMENT ON TABLE public.gitrepository IS 'Git repository';


COMMENT ON COLUMN public.gitrepository.registrant IS 'The user who registered the repository.';


COMMENT ON COLUMN public.gitrepository.owner IS 'The owner of the repository.';


COMMENT ON COLUMN public.gitrepository.project IS 'The project that this repository belongs to.';


COMMENT ON COLUMN public.gitrepository.distribution IS 'The distribution that this repository belongs to.';


COMMENT ON COLUMN public.gitrepository.sourcepackagename IS 'The source package that this repository belongs to.';


COMMENT ON COLUMN public.gitrepository.name IS 'The name of this repository.';


COMMENT ON COLUMN public.gitrepository.information_type IS 'Enum describing what type of information is stored, such as type of private or security related data, and used to determine how to apply an access policy.';


COMMENT ON COLUMN public.gitrepository.owner_default IS 'True if this repository is the default for its owner and target.';


COMMENT ON COLUMN public.gitrepository.target_default IS 'True if this repository is the default for its target.';


COMMENT ON COLUMN public.gitrepository.description IS 'A short description of this repository.';


COMMENT ON COLUMN public.gitrepository.reviewer IS 'The reviewer (person or) team are able to transition merge proposals targeted at the repository through the CODE_APPROVED state.';


COMMENT ON COLUMN public.gitrepository.default_branch IS 'The reference path of this repository''s default branch, or "HEAD".';


COMMENT ON COLUMN public.gitrepository.repository_type IS 'Repositories are currently one of HOSTED (1) or IMPORTED (3).';


CREATE SEQUENCE public.gitrepository_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gitrepository_id_seq OWNED BY public.gitrepository.id;


CREATE TABLE public.gitrule (
    id integer NOT NULL,
    repository integer NOT NULL,
    "position" integer NOT NULL,
    ref_pattern text NOT NULL,
    creator integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.gitrule IS 'An access rule for a Git repository.';


COMMENT ON COLUMN public.gitrule.repository IS 'The repository that this rule is for.';


COMMENT ON COLUMN public.gitrule."position" IS 'The position of this rule in its repository''s rule order.';


COMMENT ON COLUMN public.gitrule.ref_pattern IS 'The pattern of references matched by this rule.';


COMMENT ON COLUMN public.gitrule.creator IS 'The user who created this rule.';


COMMENT ON COLUMN public.gitrule.date_created IS 'The time when this rule was created.';


COMMENT ON COLUMN public.gitrule.date_last_modified IS 'The time when this rule was last modified.';


CREATE SEQUENCE public.gitrule_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gitrule_id_seq OWNED BY public.gitrule.id;


CREATE TABLE public.gitrulegrant (
    id integer NOT NULL,
    repository integer NOT NULL,
    rule integer NOT NULL,
    grantee_type integer NOT NULL,
    grantee integer,
    can_create boolean DEFAULT false NOT NULL,
    can_push boolean DEFAULT false NOT NULL,
    can_force_push boolean DEFAULT false NOT NULL,
    grantor integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT has_grantee CHECK (((grantee_type = 2) = (grantee IS NOT NULL)))
);


COMMENT ON TABLE public.gitrulegrant IS 'An access grant for a Git repository rule.';


COMMENT ON COLUMN public.gitrulegrant.repository IS 'The repository that this grant is for.';


COMMENT ON COLUMN public.gitrulegrant.rule IS 'The rule that this grant is for.';


COMMENT ON COLUMN public.gitrulegrant.grantee_type IS 'The type of entity being granted access.';


COMMENT ON COLUMN public.gitrulegrant.grantee IS 'The person or team being granted access.';


COMMENT ON COLUMN public.gitrulegrant.can_create IS 'Whether creating references is allowed.';


COMMENT ON COLUMN public.gitrulegrant.can_push IS 'Whether pushing references is allowed.';


COMMENT ON COLUMN public.gitrulegrant.can_force_push IS 'Whether force-pushing references is allowed.';


COMMENT ON COLUMN public.gitrulegrant.grantor IS 'The user who created this grant.';


COMMENT ON COLUMN public.gitrulegrant.date_created IS 'The time when this grant was created.';


COMMENT ON COLUMN public.gitrulegrant.date_last_modified IS 'The time when this grant was last modified.';


CREATE SEQUENCE public.gitrulegrant_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gitrulegrant_id_seq OWNED BY public.gitrulegrant.id;


CREATE TABLE public.gitsubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    repository integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    notification_level integer DEFAULT 1 NOT NULL,
    max_diff_lines integer,
    review_level integer DEFAULT 0 NOT NULL,
    subscribed_by integer NOT NULL,
    paths text
);


COMMENT ON TABLE public.gitsubscription IS 'An association between a person or team and a Git repository.';


COMMENT ON COLUMN public.gitsubscription.person IS 'The person or team associated with the repository.';


COMMENT ON COLUMN public.gitsubscription.repository IS 'The repository associated with the person or team.';


COMMENT ON COLUMN public.gitsubscription.notification_level IS 'The level of email the person wants to receive from repository updates.';


COMMENT ON COLUMN public.gitsubscription.max_diff_lines IS 'If the generated diff for a revision is larger than this number, then the diff is not sent in the notification email.';


COMMENT ON COLUMN public.gitsubscription.review_level IS 'The level of email the person wants to receive from review activity.';


COMMENT ON COLUMN public.gitsubscription.subscribed_by IS 'The person who created this subscription.';


COMMENT ON COLUMN public.gitsubscription.paths IS 'A JSON-encoded list of patterns matching subscribed reference paths.';


CREATE SEQUENCE public.gitsubscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gitsubscription_id_seq OWNED BY public.gitsubscription.id;


CREATE TABLE public.gpgkey (
    id integer NOT NULL,
    owner integer NOT NULL,
    keyid text NOT NULL,
    fingerprint text NOT NULL,
    active boolean NOT NULL,
    algorithm integer NOT NULL,
    keysize integer NOT NULL,
    can_encrypt boolean DEFAULT false NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT valid_fingerprint CHECK (public.valid_fingerprint(fingerprint)),
    CONSTRAINT valid_keyid CHECK (public.valid_keyid(keyid))
);


COMMENT ON TABLE public.gpgkey IS 'A GPG key belonging to a Person';


COMMENT ON COLUMN public.gpgkey.keyid IS 'The 8 character GPG key id, uppercase and no whitespace';


COMMENT ON COLUMN public.gpgkey.fingerprint IS 'The 40 character GPG fingerprint, uppercase and no whitespace';


COMMENT ON COLUMN public.gpgkey.active IS 'True if this key is active for use in Launchpad context, false could be deactivated by user or revoked in the global key ring.';


COMMENT ON COLUMN public.gpgkey.algorithm IS 'The algorithm used to generate this key. Valid values defined in dbschema.GPGKeyAlgorithms';


COMMENT ON COLUMN public.gpgkey.keysize IS 'Size of the key in bits, as reported by GPG. We may refuse to deal with keysizes < 768 bits in the future.';


COMMENT ON COLUMN public.gpgkey.can_encrypt IS 'Whether the key has been validated for use in encryption (as opposed to just signing)';


CREATE SEQUENCE public.gpgkey_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gpgkey_id_seq OWNED BY public.gpgkey.id;


CREATE TABLE public.hwdevice (
    id integer NOT NULL,
    bus_vendor_id integer NOT NULL,
    bus_product_id text NOT NULL,
    variant text,
    name text NOT NULL,
    submissions integer NOT NULL
);


COMMENT ON TABLE public.hwdevice IS 'Basic information on devices.';


COMMENT ON COLUMN public.hwdevice.bus_vendor_id IS 'A reference to a HWVendorID record.';


COMMENT ON COLUMN public.hwdevice.bus_product_id IS 'The bus product ID of a device';


COMMENT ON COLUMN public.hwdevice.variant IS 'An optional additional description for a device that shares its vendor and product ID with another, technically different, device.';


COMMENT ON COLUMN public.hwdevice.name IS 'The human readable product name of the device.';


COMMENT ON COLUMN public.hwdevice.submissions IS 'The number of submissions that contain this device.';


CREATE SEQUENCE public.hwdevice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwdevice_id_seq OWNED BY public.hwdevice.id;


CREATE TABLE public.hwdeviceclass (
    id integer NOT NULL,
    device integer NOT NULL,
    main_class integer NOT NULL,
    sub_class integer
);


COMMENT ON TABLE public.hwdeviceclass IS 'Capabilities of a device.';


COMMENT ON COLUMN public.hwdeviceclass.device IS 'A reference to a device.';


COMMENT ON COLUMN public.hwdeviceclass.main_class IS 'The main class of a device. Legal values are defined by the HWMainClass enumeration.';


COMMENT ON COLUMN public.hwdeviceclass.sub_class IS 'The sub-class of a device. Legal values are defined by the HWSubClass enumeration.';


CREATE SEQUENCE public.hwdeviceclass_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwdeviceclass_id_seq OWNED BY public.hwdeviceclass.id;


CREATE TABLE public.hwdevicedriverlink (
    id integer NOT NULL,
    device integer NOT NULL,
    driver integer
);


COMMENT ON TABLE public.hwdevicedriverlink IS 'Combinations of devices and drivers mentioned in submissions.';


COMMENT ON COLUMN public.hwdevicedriverlink.device IS 'The device controlled by the driver.';


COMMENT ON COLUMN public.hwdevicedriverlink.driver IS 'The driver controlling the device.';


CREATE SEQUENCE public.hwdevicedriverlink_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwdevicedriverlink_id_seq OWNED BY public.hwdevicedriverlink.id;


CREATE TABLE public.hwdevicenamevariant (
    id integer NOT NULL,
    vendor_name integer NOT NULL,
    product_name text NOT NULL,
    device integer NOT NULL,
    submissions integer NOT NULL
);


COMMENT ON TABLE public.hwdevicenamevariant IS 'Alternative vendor and product names of devices.';


COMMENT ON COLUMN public.hwdevicenamevariant.vendor_name IS 'The alternative vendor name.';


COMMENT ON COLUMN public.hwdevicenamevariant.product_name IS 'The alternative product name.';


COMMENT ON COLUMN public.hwdevicenamevariant.device IS 'The device named by this alternative vendor and product names.';


COMMENT ON COLUMN public.hwdevicenamevariant.submissions IS 'The number of submissions containing this alternative vendor and product name.';


CREATE SEQUENCE public.hwdevicenamevariant_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwdevicenamevariant_id_seq OWNED BY public.hwdevicenamevariant.id;


CREATE TABLE public.hwdmihandle (
    id integer NOT NULL,
    handle integer NOT NULL,
    type integer NOT NULL,
    submission integer
);


COMMENT ON TABLE public.hwdmihandle IS 'A DMI Handle appearing in the DMI data of a submission.';


COMMENT ON COLUMN public.hwdmihandle.handle IS 'The ID of the handle.';


COMMENT ON COLUMN public.hwdmihandle.type IS 'The type of the handle.';


CREATE SEQUENCE public.hwdmihandle_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwdmihandle_id_seq OWNED BY public.hwdmihandle.id;


CREATE TABLE public.hwdmivalue (
    id integer NOT NULL,
    key text,
    value text,
    handle integer NOT NULL
);


COMMENT ON TABLE public.hwdmivalue IS 'Key/value pairs of DMI data of a handle.';


COMMENT ON COLUMN public.hwdmivalue.key IS 'The key.';


COMMENT ON COLUMN public.hwdmivalue.value IS 'The value';


COMMENT ON COLUMN public.hwdmivalue.handle IS 'The handle to which this key/value pair belongs.';


CREATE SEQUENCE public.hwdmivalue_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwdmivalue_id_seq OWNED BY public.hwdmivalue.id;


CREATE TABLE public.hwdriver (
    id integer NOT NULL,
    package_name text,
    name text NOT NULL,
    license integer
);


COMMENT ON TABLE public.hwdriver IS 'Information about a driver for a device';


COMMENT ON COLUMN public.hwdriver.package_name IS 'The Debian package name a driver is a part of';


COMMENT ON COLUMN public.hwdriver.name IS 'The name of a driver.';


CREATE SEQUENCE public.hwdriver_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwdriver_id_seq OWNED BY public.hwdriver.id;


CREATE VIEW public.hwdrivernames AS
 SELECT DISTINCT ON (hwdriver.name) hwdriver.id,
    hwdriver.name
   FROM public.hwdriver
  ORDER BY hwdriver.name, hwdriver.id;


COMMENT ON VIEW public.hwdrivernames IS 'A view returning the distinct driver names stored in HWDriver.';


COMMENT ON COLUMN public.hwdrivernames.name IS 'The name of a driver.';


CREATE VIEW public.hwdriverpackagenames AS
 SELECT DISTINCT ON (hwdriver.package_name) hwdriver.id,
    hwdriver.package_name
   FROM public.hwdriver
  ORDER BY hwdriver.package_name, hwdriver.id;


COMMENT ON VIEW public.hwdriverpackagenames IS 'A view returning the distinct Debian package names stored in HWDriver.';


COMMENT ON COLUMN public.hwdriverpackagenames.package_name IS 'The Debian package name a driver is a part of.';


CREATE TABLE public.hwsubmission (
    id integer NOT NULL,
    date_created timestamp without time zone NOT NULL,
    date_submitted timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    format integer NOT NULL,
    status integer DEFAULT 1 NOT NULL,
    private boolean NOT NULL,
    contactable boolean NOT NULL,
    submission_key text NOT NULL,
    owner integer,
    distroarchseries integer,
    raw_submission integer NOT NULL,
    system_fingerprint integer NOT NULL,
    raw_emailaddress text
);


COMMENT ON TABLE public.hwsubmission IS 'Raw HWDB submission data';


COMMENT ON COLUMN public.hwsubmission.date_created IS 'Date and time of the submission (generated by the client).';


COMMENT ON COLUMN public.hwsubmission.date_submitted IS 'Date and time of the submission (generated by the server).';


COMMENT ON COLUMN public.hwsubmission.format IS 'The format version of the submitted data, as given by the HWDB client. See HWSubmissionFormat for valid values.';


COMMENT ON COLUMN public.hwsubmission.status IS 'The status of the submission. See HWSubmissionProcessingStatus for valid values.';


COMMENT ON COLUMN public.hwsubmission.private IS 'If false, the submitter allows public access to the data. If true, the data may be used only for statistical purposes.';


COMMENT ON COLUMN public.hwsubmission.contactable IS 'If True, the submitter agrees to be contacted by upstream developers and package maintainers for tests etc.';


COMMENT ON COLUMN public.hwsubmission.submission_key IS 'A unique submission ID.';


COMMENT ON COLUMN public.hwsubmission.owner IS 'A reference to the Person table: The owner/submitter of the data.';


COMMENT ON COLUMN public.hwsubmission.distroarchseries IS 'A reference to the distroarchseries of the submission. This value is null, if the submitted values for distribution, distroseries and architecture do not match an existing entry in the Distroarchseries table.';


COMMENT ON COLUMN public.hwsubmission.raw_submission IS 'A reference to a row of LibraryFileAlias. The library file contains the raw submission data.';


COMMENT ON COLUMN public.hwsubmission.system_fingerprint IS 'A reference to an entry of the HWDBSystemFingerPrint table. This table stores the system name as returned by HAL (system.vendor, system.product)';


COMMENT ON COLUMN public.hwsubmission.raw_emailaddress IS 'The email address of the submitter.';


CREATE SEQUENCE public.hwsubmission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwsubmission_id_seq OWNED BY public.hwsubmission.id;


CREATE TABLE public.hwsubmissionbug (
    id integer NOT NULL,
    submission integer NOT NULL,
    bug integer NOT NULL
);


COMMENT ON TABLE public.hwsubmissionbug IS 'Link bugs to HWDB submissions';


CREATE SEQUENCE public.hwsubmissionbug_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwsubmissionbug_id_seq OWNED BY public.hwsubmissionbug.id;


CREATE TABLE public.hwsubmissiondevice (
    id integer NOT NULL,
    device_driver_link integer NOT NULL,
    submission integer NOT NULL,
    parent integer,
    hal_device_id integer NOT NULL
);


COMMENT ON TABLE public.hwsubmissiondevice IS 'Links between devices and submissions.';


COMMENT ON COLUMN public.hwsubmissiondevice.device_driver_link IS 'The combination (device, driver) mentioned in a submission.';


COMMENT ON COLUMN public.hwsubmissiondevice.submission IS 'The submission mentioning this (device, driver) combination.';


COMMENT ON COLUMN public.hwsubmissiondevice.parent IS 'The parent device of this device.';


COMMENT ON COLUMN public.hwsubmissiondevice.hal_device_id IS 'The ID of the HAL node of this device in the submitted data.';


CREATE SEQUENCE public.hwsubmissiondevice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwsubmissiondevice_id_seq OWNED BY public.hwsubmissiondevice.id;


CREATE TABLE public.hwsystemfingerprint (
    id integer NOT NULL,
    fingerprint text NOT NULL
);


COMMENT ON TABLE public.hwsystemfingerprint IS 'A distinct list of "fingerprints" (HAL system.name, system.vendor) from raw submission data';


COMMENT ON COLUMN public.hwsystemfingerprint.fingerprint IS 'The fingerprint';


CREATE SEQUENCE public.hwsystemfingerprint_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwsystemfingerprint_id_seq OWNED BY public.hwsystemfingerprint.id;


CREATE TABLE public.hwtest (
    id integer NOT NULL,
    namespace text,
    name text NOT NULL,
    version text NOT NULL
);


COMMENT ON TABLE public.hwtest IS 'General information about a device test.';


COMMENT ON COLUMN public.hwtest.namespace IS 'The namespace of a test.';


COMMENT ON COLUMN public.hwtest.name IS 'The name of a test.';


CREATE SEQUENCE public.hwtest_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwtest_id_seq OWNED BY public.hwtest.id;


CREATE TABLE public.hwtestanswer (
    id integer NOT NULL,
    test integer NOT NULL,
    choice integer,
    intval integer,
    floatval double precision,
    unit text,
    comment text,
    language integer,
    submission integer NOT NULL,
    CONSTRAINT hwtestanswer_check CHECK (((((choice IS NULL) AND (unit IS NOT NULL)) AND ((intval IS NULL) <> (floatval IS NULL))) OR ((((choice IS NOT NULL) AND (unit IS NULL)) AND (intval IS NULL)) AND (floatval IS NULL))))
);


COMMENT ON TABLE public.hwtestanswer IS 'The answer for a test from a submission. This can be either a multiple choice selection or a numerical value. Exactly one of the columns choice, intval, floatval must be non-null.';


COMMENT ON COLUMN public.hwtestanswer.test IS 'The test answered by this answer.';


COMMENT ON COLUMN public.hwtestanswer.choice IS 'The selected value of a multiple choice test.';


COMMENT ON COLUMN public.hwtestanswer.intval IS 'The integer result of a test with a numerical result.';


COMMENT ON COLUMN public.hwtestanswer.floatval IS 'The double precision floating point number result of a test with a numerical result.';


COMMENT ON COLUMN public.hwtestanswer.unit IS 'The physical unit of a test with a numerical result.';


CREATE SEQUENCE public.hwtestanswer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwtestanswer_id_seq OWNED BY public.hwtestanswer.id;


CREATE TABLE public.hwtestanswerchoice (
    id integer NOT NULL,
    choice text NOT NULL,
    test integer NOT NULL
);


COMMENT ON TABLE public.hwtestanswerchoice IS 'Choice values of multiple choice tests/questions.';


COMMENT ON COLUMN public.hwtestanswerchoice.choice IS 'The choice value.';


COMMENT ON COLUMN public.hwtestanswerchoice.test IS 'The test this choice belongs to.';


CREATE SEQUENCE public.hwtestanswerchoice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwtestanswerchoice_id_seq OWNED BY public.hwtestanswerchoice.id;


CREATE TABLE public.hwtestanswercount (
    id integer NOT NULL,
    test integer NOT NULL,
    distroarchseries integer,
    choice integer,
    average double precision,
    sum_square double precision,
    unit text,
    num_answers integer NOT NULL,
    CONSTRAINT hwtestanswercount_check CHECK ((((((choice IS NULL) AND (average IS NOT NULL)) AND (sum_square IS NOT NULL)) AND (unit IS NOT NULL)) OR ((((choice IS NOT NULL) AND (average IS NULL)) AND (sum_square IS NULL)) AND (unit IS NULL))))
);


COMMENT ON TABLE public.hwtestanswercount IS 'Accumulated results of tests. Either the column choice or the columns average and sum_square must be non-null.';


COMMENT ON COLUMN public.hwtestanswercount.test IS 'The test.';


COMMENT ON COLUMN public.hwtestanswercount.distroarchseries IS 'The distroarchseries for which results are accumulated,';


COMMENT ON COLUMN public.hwtestanswercount.choice IS 'The choice value of a multiple choice test.';


COMMENT ON COLUMN public.hwtestanswercount.average IS 'The average value of the result of a numerical test.';


COMMENT ON COLUMN public.hwtestanswercount.sum_square IS 'The sum of the squares of the results of a numerical test.';


COMMENT ON COLUMN public.hwtestanswercount.unit IS 'The physical unit of a numerical test result.';


COMMENT ON COLUMN public.hwtestanswercount.num_answers IS 'The number of submissions from which the result is accumulated.';


CREATE SEQUENCE public.hwtestanswercount_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwtestanswercount_id_seq OWNED BY public.hwtestanswercount.id;


CREATE TABLE public.hwtestanswercountdevice (
    id integer NOT NULL,
    answer integer NOT NULL,
    device_driver integer NOT NULL
);


COMMENT ON TABLE public.hwtestanswercountdevice IS 'Association of accumulated test results and device/driver combinations.';


COMMENT ON COLUMN public.hwtestanswercountdevice.answer IS 'The test answer.';


COMMENT ON COLUMN public.hwtestanswercountdevice.device_driver IS 'The device/driver combination.';


CREATE SEQUENCE public.hwtestanswercountdevice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwtestanswercountdevice_id_seq OWNED BY public.hwtestanswercountdevice.id;


CREATE TABLE public.hwtestanswerdevice (
    id integer NOT NULL,
    answer integer NOT NULL,
    device_driver integer NOT NULL
);


COMMENT ON TABLE public.hwtestanswerdevice IS 'Association of test results and device/driver combinations.';


COMMENT ON COLUMN public.hwtestanswerdevice.answer IS 'The test answer.';


COMMENT ON COLUMN public.hwtestanswerdevice.device_driver IS 'The device/driver combination.';


CREATE SEQUENCE public.hwtestanswerdevice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwtestanswerdevice_id_seq OWNED BY public.hwtestanswerdevice.id;


CREATE TABLE public.hwvendorid (
    id integer NOT NULL,
    bus integer NOT NULL,
    vendor_id_for_bus text NOT NULL,
    vendor_name integer NOT NULL
);


COMMENT ON TABLE public.hwvendorid IS 'Associates tuples (bus, vendor ID for this bus) with vendor names.';


COMMENT ON COLUMN public.hwvendorid.bus IS 'The bus.';


COMMENT ON COLUMN public.hwvendorid.vendor_id_for_bus IS 'The ID of a vendor for the bus given by column `bus`';


CREATE SEQUENCE public.hwvendorid_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwvendorid_id_seq OWNED BY public.hwvendorid.id;


CREATE TABLE public.hwvendorname (
    id integer NOT NULL,
    name text NOT NULL
);


COMMENT ON TABLE public.hwvendorname IS 'A list of hardware vendor names.';


COMMENT ON COLUMN public.hwvendorname.name IS 'The name of a vendor.';


CREATE SEQUENCE public.hwvendorname_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hwvendorname_id_seq OWNED BY public.hwvendorname.id;


CREATE TABLE public.incrementaldiff (
    id integer NOT NULL,
    diff integer NOT NULL,
    branch_merge_proposal integer NOT NULL,
    old_revision integer NOT NULL,
    new_revision integer NOT NULL
);


COMMENT ON TABLE public.incrementaldiff IS 'Incremental diffs for merge proposals.';


COMMENT ON COLUMN public.incrementaldiff.diff IS 'The contents of the diff.';


COMMENT ON COLUMN public.incrementaldiff.branch_merge_proposal IS 'The merge proposal the diff is for.';


COMMENT ON COLUMN public.incrementaldiff.old_revision IS 'The revision the diff is from.';


COMMENT ON COLUMN public.incrementaldiff.new_revision IS 'The revision the diff is to.';


CREATE SEQUENCE public.incrementaldiff_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.incrementaldiff_id_seq OWNED BY public.incrementaldiff.id;


CREATE TABLE public.ircid (
    id integer NOT NULL,
    person integer NOT NULL,
    network text NOT NULL,
    nickname text NOT NULL
);


CREATE SEQUENCE public.ircid_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ircid_id_seq OWNED BY public.ircid.id;


CREATE TABLE public.jabberid (
    id integer NOT NULL,
    person integer NOT NULL,
    jabberid text NOT NULL
);


CREATE SEQUENCE public.jabberid_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.jabberid_id_seq OWNED BY public.jabberid.id;


CREATE TABLE public.job (
    id integer NOT NULL,
    requester integer,
    reason text,
    status integer NOT NULL,
    progress integer,
    last_report_seen timestamp without time zone,
    next_report_due timestamp without time zone,
    attempt_count integer DEFAULT 0 NOT NULL,
    max_retries integer DEFAULT 0 NOT NULL,
    log text,
    scheduled_start timestamp without time zone,
    lease_expires timestamp without time zone,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_started timestamp without time zone,
    date_finished timestamp without time zone,
    json_data text,
    job_type integer
);


COMMENT ON TABLE public.job IS 'Common info about a job.';


COMMENT ON COLUMN public.job.requester IS 'Ther person who requested this job (if applicable).';


COMMENT ON COLUMN public.job.reason IS 'The reason that this job was created (if applicable)';


COMMENT ON COLUMN public.job.status IS 'An enum (JobStatus) indicating the job status, one of: new, in-progress, complete, failed, cancelling, cancelled.';


COMMENT ON COLUMN public.job.progress IS 'The percentage complete.  Can be NULL for some jobs that do not report progress.';


COMMENT ON COLUMN public.job.last_report_seen IS 'The last time the progress was reported.';


COMMENT ON COLUMN public.job.next_report_due IS 'The next time a progress report is expected.';


COMMENT ON COLUMN public.job.attempt_count IS 'The number of times this job has been attempted.';


COMMENT ON COLUMN public.job.max_retries IS 'The maximum number of retries valid for this job.';


COMMENT ON COLUMN public.job.log IS 'If provided, this is the tail of the log file being generated by the running job.';


COMMENT ON COLUMN public.job.scheduled_start IS 'The time when the job should start';


COMMENT ON COLUMN public.job.lease_expires IS 'The time when the lease expires.';


COMMENT ON COLUMN public.job.date_created IS 'The time when the job was created.';


COMMENT ON COLUMN public.job.date_started IS 'If the job has started, the time when the job started.';


COMMENT ON COLUMN public.job.date_finished IS 'If the job has finished, the time when the job finished.';


CREATE SEQUENCE public.job_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.job_id_seq OWNED BY public.job.id;


CREATE TABLE public.karma (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    person integer NOT NULL,
    action integer NOT NULL,
    product integer,
    distribution integer,
    sourcepackagename integer
)
WITH (fillfactor='100');


COMMENT ON TABLE public.karma IS 'Used to quantify all the ''operations'' a user performs inside the system, which maybe reporting and fixing bugs, uploading packages, end-user support, wiki editting, etc.';


COMMENT ON COLUMN public.karma.datecreated IS 'A timestamp for the assignment of this Karma.';


COMMENT ON COLUMN public.karma.person IS 'The Person for wich this Karma was assigned.';


COMMENT ON COLUMN public.karma.action IS 'A foreign key to the KarmaAction table.';


COMMENT ON COLUMN public.karma.product IS 'The Project to which this Product belongs.  An entry on this table with a non-NULL Project and a NULL Product represents the total karma of the person across all products of that project..';


COMMENT ON COLUMN public.karma.distribution IS 'The Distribution on which a person performed an action that resulted on this karma.';


COMMENT ON COLUMN public.karma.sourcepackagename IS 'The SourcePackageName on which a person performed an action that resulted on this karma.';


CREATE SEQUENCE public.karma_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.karma_id_seq OWNED BY public.karma.id;


CREATE TABLE public.karmaaction (
    id integer NOT NULL,
    category integer,
    points integer,
    name text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL
);


COMMENT ON TABLE public.karmaaction IS 'Stores all the actions that would give karma to the user which performed it.';


COMMENT ON COLUMN public.karmaaction.category IS 'A dbschema value used to group actions together.';


COMMENT ON COLUMN public.karmaaction.points IS 'The number of points this action is worth of.';


COMMENT ON COLUMN public.karmaaction.name IS 'The unique name of this action.';


CREATE SEQUENCE public.karmaaction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.karmaaction_id_seq OWNED BY public.karmaaction.id;


CREATE TABLE public.karmacache (
    id integer NOT NULL,
    person integer NOT NULL,
    category integer,
    karmavalue integer NOT NULL,
    product integer,
    distribution integer,
    sourcepackagename integer,
    project integer,
    CONSTRAINT just_distribution CHECK (((distribution IS NULL) OR ((product IS NULL) AND (project IS NULL)))),
    CONSTRAINT just_product CHECK (((product IS NULL) OR ((project IS NULL) AND (distribution IS NULL)))),
    CONSTRAINT just_project CHECK (((project IS NULL) OR ((product IS NULL) AND (distribution IS NULL)))),
    CONSTRAINT sourcepackagename_requires_distribution CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);


COMMENT ON TABLE public.karmacache IS 'Stores a cached value of a person''s karma points, grouped by the action category and the context where that action was performed.';


COMMENT ON COLUMN public.karmacache.person IS 'The person which performed the actions of this category, and thus got the karma.';


COMMENT ON COLUMN public.karmacache.category IS 'The category of the actions.';


COMMENT ON COLUMN public.karmacache.karmavalue IS 'The karma points of all actions of this category performed by this person on this context (product/distribution).';


CREATE SEQUENCE public.karmacache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.karmacache_id_seq OWNED BY public.karmacache.id;


CREATE TABLE public.karmacategory (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL
);


COMMENT ON TABLE public.karmacategory IS 'A category of karma. This allows us to
present an overall picture of the different areas where a user has been
active.';


CREATE SEQUENCE public.karmacategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.karmacategory_id_seq OWNED BY public.karmacategory.id;


CREATE TABLE public.karmatotalcache (
    id integer NOT NULL,
    person integer NOT NULL,
    karma_total integer NOT NULL
);


CREATE SEQUENCE public.karmatotalcache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.karmatotalcache_id_seq OWNED BY public.karmatotalcache.id;


CREATE TABLE public.language (
    id integer NOT NULL,
    code text NOT NULL,
    englishname text NOT NULL,
    nativename text,
    pluralforms integer,
    pluralexpression text,
    visible boolean NOT NULL,
    direction integer DEFAULT 0 NOT NULL,
    uuid text,
    CONSTRAINT valid_language CHECK (((pluralforms IS NULL) = (pluralexpression IS NULL)))
);


COMMENT ON TABLE public.language IS 'A human language.';


COMMENT ON COLUMN public.language.code IS 'The ISO 639 code for this language';


COMMENT ON COLUMN public.language.englishname IS 'The english name for this language';


COMMENT ON COLUMN public.language.nativename IS 'The name of this language in the language itself';


COMMENT ON COLUMN public.language.pluralforms IS 'The number of plural forms this language has';


COMMENT ON COLUMN public.language.pluralexpression IS 'The plural expression for this language, as used by gettext';


COMMENT ON COLUMN public.language.visible IS 'Whether this language should usually be visible or not';


COMMENT ON COLUMN public.language.direction IS 'The direction that text is written in this language';


COMMENT ON COLUMN public.language.uuid IS 'Mozilla language pack unique ID';


CREATE SEQUENCE public.language_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.language_id_seq OWNED BY public.language.id;


CREATE TABLE public.languagepack (
    id integer NOT NULL,
    file integer NOT NULL,
    date_exported timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_used timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    distroseries integer NOT NULL,
    type integer DEFAULT 1 NOT NULL,
    updates integer,
    CONSTRAINT valid_updates CHECK ((((type = 2) AND (updates IS NOT NULL)) OR ((type = 1) AND (updates IS NULL))))
);


COMMENT ON TABLE public.languagepack IS 'Store exported language packs for DistroSeries.';


COMMENT ON COLUMN public.languagepack.file IS 'Librarian file where the language pack is stored.';


COMMENT ON COLUMN public.languagepack.date_exported IS 'When was exported the language pack.';


COMMENT ON COLUMN public.languagepack.date_last_used IS 'When did we stop using the language pack. It''s used to decide whether we can remove it completely from the system. When it''s being used, its value is NULL';


COMMENT ON COLUMN public.languagepack.distroseries IS 'The distribution series from where this language pack was exported.';


COMMENT ON COLUMN public.languagepack.type IS 'Type of language pack. There are two types available, 1: Full export, 2: Update export based on language_pack_that_updates export.';


COMMENT ON COLUMN public.languagepack.updates IS 'The LanguagePack that this one updates.';


CREATE SEQUENCE public.languagepack_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.languagepack_id_seq OWNED BY public.languagepack.id;


CREATE VIEW public.latestdatabasediskutilization AS
 SELECT databasediskutilization.date_created,
    databasediskutilization.namespace,
    databasediskutilization.name,
    databasediskutilization.sub_namespace,
    databasediskutilization.sub_name,
    databasediskutilization.kind,
    databasediskutilization.sort,
    databasediskutilization.table_len,
    databasediskutilization.tuple_count,
    databasediskutilization.tuple_len,
    databasediskutilization.tuple_percent,
    databasediskutilization.dead_tuple_count,
    databasediskutilization.dead_tuple_len,
    databasediskutilization.dead_tuple_percent,
    databasediskutilization.free_space,
    databasediskutilization.free_percent
   FROM public.databasediskutilization
  WHERE (databasediskutilization.date_created = ( SELECT max(databasediskutilization_1.date_created) AS max
           FROM public.databasediskutilization databasediskutilization_1));


CREATE TABLE public.latestpersonsourcepackagereleasecache (
    id integer NOT NULL,
    publication integer NOT NULL,
    date_uploaded timestamp without time zone NOT NULL,
    creator integer,
    maintainer integer,
    archive_purpose integer NOT NULL,
    upload_archive integer NOT NULL,
    upload_distroseries integer NOT NULL,
    sourcepackagename integer NOT NULL,
    sourcepackagerelease integer NOT NULL
);


COMMENT ON TABLE public.latestpersonsourcepackagereleasecache IS 'LatestPersonSourcePackageReleaseCache: The most recent published source package releases for a given (distroseries, archive, sourcepackage).';


COMMENT ON COLUMN public.latestpersonsourcepackagereleasecache.date_uploaded IS 'The date/time on which the source was actually published into the archive.';


COMMENT ON COLUMN public.latestpersonsourcepackagereleasecache.creator IS 'The creator of the source package release.';


COMMENT ON COLUMN public.latestpersonsourcepackagereleasecache.maintainer IS 'The maintainer of the source package in the DSC.';


COMMENT ON COLUMN public.latestpersonsourcepackagereleasecache.archive_purpose IS 'The purpose of the archive, e.g. COMMERCIAL.  See the ArchivePurpose DBSchema item.';


COMMENT ON COLUMN public.latestpersonsourcepackagereleasecache.upload_archive IS 'The target archive for the release.';


COMMENT ON COLUMN public.latestpersonsourcepackagereleasecache.upload_distroseries IS 'The distroseries into which the sourcepackagerelease was published.';


COMMENT ON COLUMN public.latestpersonsourcepackagereleasecache.sourcepackagename IS 'The SourcePackageName of the release.';


COMMENT ON COLUMN public.latestpersonsourcepackagereleasecache.sourcepackagerelease IS 'The sourcepackagerelease which was published.';


CREATE SEQUENCE public.latestpersonsourcepackagereleasecache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.latestpersonsourcepackagereleasecache_id_seq OWNED BY public.latestpersonsourcepackagereleasecache.id;


CREATE TABLE public.launchpaddatabaserevision (
    major integer NOT NULL,
    minor integer NOT NULL,
    patch integer NOT NULL,
    start_time timestamp without time zone DEFAULT timezone('UTC'::text, transaction_timestamp()),
    end_time timestamp without time zone DEFAULT timezone('UTC'::text, clock_timestamp()),
    branch_nick text,
    revno integer,
    revid text
);


COMMENT ON TABLE public.launchpaddatabaserevision IS 'This table contains a list of the database patches that have been successfully applied to this database.';


COMMENT ON COLUMN public.launchpaddatabaserevision.major IS 'Major number. This is the version of the baseline schema the patch was made agains.';


COMMENT ON COLUMN public.launchpaddatabaserevision.minor IS 'Minor number. Patches made during development each increment the minor number.';


COMMENT ON COLUMN public.launchpaddatabaserevision.patch IS 'The patch number will hopefully always be ''0'', as it exists to support emergency patches made to the production server. eg. If production is running ''4.0.0'' and needs to have a patch applied ASAP, we would create a ''4.0.1'' patch and roll it out. We then may need to refactor all the existing ''4.x.0'' patches.';


CREATE TABLE public.launchpaddatabaseupdatelog (
    id integer NOT NULL,
    start_time timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    end_time timestamp without time zone,
    branch_nick text,
    revno integer,
    revid text
);


COMMENT ON TABLE public.launchpaddatabaseupdatelog IS 'Record of Launchpad database schema updates. When and what update.py was run.';


CREATE SEQUENCE public.launchpaddatabaseupdatelog_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.launchpaddatabaseupdatelog_id_seq OWNED BY public.launchpaddatabaseupdatelog.id;


CREATE TABLE public.launchpadstatistic (
    id integer NOT NULL,
    name text NOT NULL,
    value integer NOT NULL,
    dateupdated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL
);


COMMENT ON TABLE public.launchpadstatistic IS 'A store of system-wide statistics or other integer values, keyed by names. The names are unique and the values can be any integer. Each field has a place to store the timestamp when it was last updated, so it is possible to know how far out of date any given statistic is.';


CREATE SEQUENCE public.launchpadstatistic_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.launchpadstatistic_id_seq OWNED BY public.launchpadstatistic.id;


CREATE TABLE public.libraryfilealias (
    id integer NOT NULL,
    filename text NOT NULL,
    mimetype text NOT NULL,
    expires timestamp without time zone,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    restricted boolean DEFAULT false NOT NULL,
    hits integer DEFAULT 0 NOT NULL,
    content bigint,
    CONSTRAINT valid_filename CHECK ((filename !~~ '%/%'::text))
);


COMMENT ON TABLE public.libraryfilealias IS 'LibraryFileAlias: A librarian file''s alias. The librarian stores, along with the file contents, a record stating the file name and mimetype. This table represents it.';


COMMENT ON COLUMN public.libraryfilealias.filename IS 'The name of the file. E.g. "foo_1.0-1_i386.deb"';


COMMENT ON COLUMN public.libraryfilealias.mimetype IS 'The mime type of the file. E.g. "application/x-debian-package"';


COMMENT ON COLUMN public.libraryfilealias.expires IS 'The expiry date of this file. If NULL, this item may be removed as soon as it is no longer referenced. If set, the item will not be removed until this date. Once the date is passed, the file may be removed from disk even if this item is still being referenced (in which case content.deleted will be true)';


COMMENT ON COLUMN public.libraryfilealias.date_created IS 'The timestamp when this alias was created.';


COMMENT ON COLUMN public.libraryfilealias.restricted IS 'Is this file available only from the restricted librarian?';


COMMENT ON COLUMN public.libraryfilealias.hits IS 'The number of times this file has been downloaded.';


COMMENT ON COLUMN public.libraryfilealias.content IS 'The libraryfilecontent which is the data in this file.';


CREATE SEQUENCE public.libraryfilealias_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.libraryfilealias_id_seq OWNED BY public.libraryfilealias.id;


CREATE TABLE public.libraryfilecontent (
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    filesize bigint NOT NULL,
    sha1 character(40) NOT NULL,
    md5 character(32) NOT NULL,
    sha256 character(64) NOT NULL,
    id bigint NOT NULL
)
WITH (fillfactor='100');


COMMENT ON TABLE public.libraryfilecontent IS 'LibraryFileContent: A librarian file''s contents. The librarian stores files in a safe and transactional way. This table represents the contents of those files within the database.';


COMMENT ON COLUMN public.libraryfilecontent.datecreated IS 'The date on which this librarian file was created';


COMMENT ON COLUMN public.libraryfilecontent.filesize IS 'The size of the file';


COMMENT ON COLUMN public.libraryfilecontent.sha1 IS 'The SHA1 sum of the file''s contents';


COMMENT ON COLUMN public.libraryfilecontent.md5 IS 'The MD5 sum of the file''s contents';


COMMENT ON COLUMN public.libraryfilecontent.sha256 IS 'The SHA256 sum of the file''s contents';


CREATE SEQUENCE public.libraryfilecontent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.libraryfilecontent_id_seq OWNED BY public.libraryfilecontent.id;


CREATE TABLE public.libraryfiledownloadcount (
    id integer NOT NULL,
    libraryfilealias integer NOT NULL,
    day date NOT NULL,
    count integer NOT NULL,
    country integer
);


COMMENT ON TABLE public.libraryfiledownloadcount IS 'The number of daily downloads for a given LibraryFileAlias.';


COMMENT ON COLUMN public.libraryfiledownloadcount.libraryfilealias IS 'The LibraryFileAlias.';


COMMENT ON COLUMN public.libraryfiledownloadcount.day IS 'The day of the downloads.';


COMMENT ON COLUMN public.libraryfiledownloadcount.count IS 'The number of downloads.';


COMMENT ON COLUMN public.libraryfiledownloadcount.country IS 'The country from where the download requests came from.';


CREATE SEQUENCE public.libraryfiledownloadcount_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.libraryfiledownloadcount_id_seq OWNED BY public.libraryfiledownloadcount.id;


CREATE TABLE public.livefs (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    owner integer NOT NULL,
    distro_series integer NOT NULL,
    name text NOT NULL,
    json_data text,
    require_virtualized boolean DEFAULT true NOT NULL,
    relative_build_score integer DEFAULT 0 NOT NULL,
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.livefs IS 'A class of buildable live filesystem images.  Rows in this table only partially define how to build an image; the rest of the information comes from LiveFSBuild.';


COMMENT ON COLUMN public.livefs.registrant IS 'The user who registered the live filesystem image.';


COMMENT ON COLUMN public.livefs.owner IS 'The owner of the live filesystem image.';


COMMENT ON COLUMN public.livefs.distro_series IS 'The DistroSeries for which the image should be built.';


COMMENT ON COLUMN public.livefs.name IS 'The name of the live filesystem image, unique per DistroSeries.';


COMMENT ON COLUMN public.livefs.json_data IS 'A JSON struct containing data for the image build.';


COMMENT ON COLUMN public.livefs.require_virtualized IS 'If True, this live filesystem image must be built only on a virtual machine.';


COMMENT ON COLUMN public.livefs.relative_build_score IS 'A delta to the build score that is applied to all builds of this live filesystem.';


CREATE SEQUENCE public.livefs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.livefs_id_seq OWNED BY public.livefs.id;


CREATE TABLE public.livefsbuild (
    id integer NOT NULL,
    requester integer NOT NULL,
    livefs integer NOT NULL,
    archive integer NOT NULL,
    distro_arch_series integer NOT NULL,
    pocket integer NOT NULL,
    unique_key text,
    json_data_override text,
    processor integer NOT NULL,
    virtualized boolean NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_started timestamp without time zone,
    date_finished timestamp without time zone,
    date_first_dispatched timestamp without time zone,
    builder integer,
    status integer NOT NULL,
    log integer,
    upload_log integer,
    dependencies text,
    failure_count integer DEFAULT 0 NOT NULL,
    build_farm_job integer NOT NULL,
    version text
);


COMMENT ON TABLE public.livefsbuild IS 'A build record for a live filesystem image.';


COMMENT ON COLUMN public.livefsbuild.requester IS 'The person who requested this live filesystem image build.';


COMMENT ON COLUMN public.livefsbuild.livefs IS 'Live filesystem image to build.';


COMMENT ON COLUMN public.livefsbuild.archive IS 'The archive that the live filesystem image should build from.';


COMMENT ON COLUMN public.livefsbuild.distro_arch_series IS 'The distroarchseries that the live filesystem image should build from.';


COMMENT ON COLUMN public.livefsbuild.pocket IS 'The pocket that the live filesystem image should build from.';


COMMENT ON COLUMN public.livefsbuild.unique_key IS 'A unique key distinguishing this build from others for the same livefs/archive/distroarchseries/pocket, or NULL.';


COMMENT ON COLUMN public.livefsbuild.json_data_override IS 'A JSON struct containing data for the image build, each key of which overrides the same key from livefs.json_data.';


COMMENT ON COLUMN public.livefsbuild.virtualized IS 'The virtualization setting required by this build farm job.';


COMMENT ON COLUMN public.livefsbuild.date_created IS 'When the build farm job record was created.';


COMMENT ON COLUMN public.livefsbuild.date_started IS 'When the build farm job started being processed.';


COMMENT ON COLUMN public.livefsbuild.date_finished IS 'When the build farm job finished being processed.';


COMMENT ON COLUMN public.livefsbuild.date_first_dispatched IS 'The instant the build was dispatched the first time.  This value will not get overridden if the build is retried.';


COMMENT ON COLUMN public.livefsbuild.builder IS 'The builder which processed this build farm job.';


COMMENT ON COLUMN public.livefsbuild.status IS 'The current build status.';


COMMENT ON COLUMN public.livefsbuild.log IS 'The log file for this build farm job stored in the librarian.';


COMMENT ON COLUMN public.livefsbuild.upload_log IS 'The upload log file for this build farm job stored in the librarian.';


COMMENT ON COLUMN public.livefsbuild.dependencies IS 'A Debian-like dependency line specifying the current missing dependencies for this build.';


COMMENT ON COLUMN public.livefsbuild.failure_count IS 'The number of consecutive failures on this job.  If excessive, the job may be terminated.';


COMMENT ON COLUMN public.livefsbuild.build_farm_job IS 'The build farm job with the base information.';


COMMENT ON COLUMN public.livefsbuild.version IS 'A version string for this build.';


CREATE SEQUENCE public.livefsbuild_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.livefsbuild_id_seq OWNED BY public.livefsbuild.id;


CREATE TABLE public.livefsfile (
    id integer NOT NULL,
    livefsbuild integer NOT NULL,
    libraryfile integer NOT NULL
);


COMMENT ON TABLE public.livefsfile IS 'A link between a live filesystem build and a file in the librarian that it produces.';


COMMENT ON COLUMN public.livefsfile.livefsbuild IS 'The live filesystem build producing this file.';


COMMENT ON COLUMN public.livefsfile.libraryfile IS 'A file in the librarian.';


CREATE SEQUENCE public.livefsfile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.livefsfile_id_seq OWNED BY public.livefsfile.id;


CREATE TABLE public.logintoken (
    id integer NOT NULL,
    requester integer,
    requesteremail text,
    email text NOT NULL,
    created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    tokentype integer NOT NULL,
    token text,
    fingerprint text,
    redirection_url text,
    date_consumed timestamp without time zone,
    CONSTRAINT valid_fingerprint CHECK (((fingerprint IS NULL) OR public.valid_fingerprint(fingerprint)))
);


COMMENT ON TABLE public.logintoken IS 'LoginToken stores one time tokens used by Launchpad for validating email addresses and other tasks that require verifying an email address is valid such as password recovery and account merging. This table will be cleaned occasionally to remove expired tokens. Expiry time is not yet defined.';


COMMENT ON COLUMN public.logintoken.requester IS 'The Person that made this request. This will be null for password recovery requests.';


COMMENT ON COLUMN public.logintoken.requesteremail IS 'The email address that was used to login when making this request. This provides an audit trail to help the end user confirm that this is a valid request. It is not a link to the EmailAddress table as this may be changed after the request is made. This field will be null for password recovery requests.';


COMMENT ON COLUMN public.logintoken.email IS 'The email address that this request was sent to.';


COMMENT ON COLUMN public.logintoken.created IS 'The timestamp that this request was made.';


COMMENT ON COLUMN public.logintoken.tokentype IS 'The type of request, as per dbschema.TokenType.';


COMMENT ON COLUMN public.logintoken.token IS 'The token (not the URL) emailed used to uniquely identify this request. This token will be used to generate a URL that when clicked on will continue a workflow.';


COMMENT ON COLUMN public.logintoken.fingerprint IS 'The GPG key fingerprint to be validated on this transaction, it means that a new register will be created relating this given key with the requester in question. The requesteremail still passing for the same usual checks.';


COMMENT ON COLUMN public.logintoken.date_consumed IS 'The date and time when this token was consumed. It''s NULL if it hasn''t been consumed yet.';


CREATE SEQUENCE public.logintoken_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.logintoken_id_seq OWNED BY public.logintoken.id;


CREATE TABLE public.lp_account (
    id integer NOT NULL,
    openid_identifier text NOT NULL
);


CREATE TABLE public.lp_openididentifier (
    identifier text NOT NULL,
    account integer NOT NULL,
    date_created timestamp without time zone NOT NULL
);


CREATE TABLE public.lp_person (
    id integer NOT NULL,
    displayname text,
    teamowner integer,
    teamdescription text,
    name text,
    language integer,
    fti public.ts2_tsvector,
    defaultmembershipperiod integer,
    defaultrenewalperiod integer,
    subscriptionpolicy integer,
    merged integer,
    datecreated timestamp without time zone,
    addressline1 text,
    addressline2 text,
    organization text,
    city text,
    province text,
    country integer,
    postcode text,
    phone text,
    homepage_content text,
    icon integer,
    mugshot integer,
    hide_email_addresses boolean,
    creation_rationale integer,
    creation_comment text,
    registrant integer,
    logo integer,
    renewal_policy integer,
    personal_standing integer,
    personal_standing_reason text,
    mail_resumption_date date,
    mailing_list_auto_subscribe_policy integer,
    mailing_list_receive_duplicates boolean,
    visibility integer,
    verbose_bugnotifications boolean,
    account integer
);


CREATE TABLE public.lp_personlocation (
    id integer NOT NULL,
    date_created timestamp without time zone,
    person integer,
    latitude double precision,
    longitude double precision,
    time_zone text,
    last_modified_by integer,
    date_last_modified timestamp without time zone,
    visible boolean,
    locked boolean
);


CREATE TABLE public.lp_teamparticipation (
    id integer NOT NULL,
    team integer,
    person integer
);


CREATE TABLE public.mailinglist (
    id integer NOT NULL,
    team integer NOT NULL,
    registrant integer NOT NULL,
    date_registered timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    reviewer integer,
    date_reviewed timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    date_activated timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    status integer DEFAULT 1 NOT NULL,
    welcome_message text
);


COMMENT ON TABLE public.mailinglist IS 'The mailing list for a team.  Teams may have zero or one mailing list, and a mailing list is associated with exactly one team.  This table manages the state changes that a team mailing list can go through, and it contains information that will be used to instruct Mailman how to create, delete, and modify mailing lists (via XMLRPC).';


COMMENT ON COLUMN public.mailinglist.team IS 'The team this mailing list is associated with.';


COMMENT ON COLUMN public.mailinglist.registrant IS 'The id of the Person who requested this list be created.';


COMMENT ON COLUMN public.mailinglist.date_registered IS 'Date the list was requested to be created';


COMMENT ON COLUMN public.mailinglist.reviewer IS 'The id of the Person who reviewed the creation request, or NULL if not yet reviewed.';


COMMENT ON COLUMN public.mailinglist.date_reviewed IS 'The date the request was reviewed, or NULL if not yet reviewed.';


COMMENT ON COLUMN public.mailinglist.date_activated IS 'The date the list was (last) activated.  If the list is not yet active, this field will be NULL.';


COMMENT ON COLUMN public.mailinglist.status IS 'The current status of the mailing list, as a dbschema.MailingListStatus value.';


COMMENT ON COLUMN public.mailinglist.welcome_message IS 'Text sent to new members when they are subscribed to the team list.  If NULL, no welcome message is sent.';


CREATE SEQUENCE public.mailinglist_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mailinglist_id_seq OWNED BY public.mailinglist.id;


CREATE TABLE public.mailinglistsubscription (
    id integer NOT NULL,
    person integer NOT NULL,
    mailing_list integer NOT NULL,
    date_joined timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    email_address integer
);


COMMENT ON TABLE public.mailinglistsubscription IS 'Track the subscriptions of a person to team mailing lists.';


COMMENT ON COLUMN public.mailinglistsubscription.person IS 'The person who is subscribed to the mailing list.';


COMMENT ON COLUMN public.mailinglistsubscription.mailing_list IS 'The mailing list this person is subscribed to.';


COMMENT ON COLUMN public.mailinglistsubscription.date_joined IS 'The date this person subscribed to the mailing list.';


COMMENT ON COLUMN public.mailinglistsubscription.email_address IS 'Which of the person''s email addresses are subscribed to the mailing list.  This may be NULL to indicate that it''s the person''s preferred address.';


CREATE SEQUENCE public.mailinglistsubscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mailinglistsubscription_id_seq OWNED BY public.mailinglistsubscription.id;


CREATE TABLE public.message (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    subject text,
    owner integer,
    parent integer,
    distribution integer,
    rfc822msgid text NOT NULL,
    fti public.ts2_tsvector,
    raw integer,
    visible boolean DEFAULT true NOT NULL
)
WITH (fillfactor='100');


COMMENT ON TABLE public.message IS 'This table stores a single RFC822-style message. Messages can be threaded (using the parent field). These messages can then be referenced from elsewhere in the system, such as the BugMessage table, integrating messageboard facilities with the rest of The Launchpad.';


COMMENT ON COLUMN public.message.subject IS 'The title text of the message, or the subject if it was an email.';


COMMENT ON COLUMN public.message.parent IS 'A "parent message". This allows for some level of threading in Messages.';


COMMENT ON COLUMN public.message.distribution IS 'The distribution in which this message originated, if we know it.';


COMMENT ON COLUMN public.message.raw IS 'The original unadulterated message if it arrived via email. This is required to provide access to the original, undecoded message.';


COMMENT ON COLUMN public.message.visible IS 'If false, the message is hidden and should not be shown in any UI.';


CREATE SEQUENCE public.message_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.message_id_seq OWNED BY public.message.id;


CREATE TABLE public.messageapproval (
    id integer NOT NULL,
    posted_by integer NOT NULL,
    mailing_list integer NOT NULL,
    posted_message integer NOT NULL,
    posted_date timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    disposed_by integer,
    disposal_date timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    reason text,
    message integer NOT NULL
);


COMMENT ON TABLE public.messageapproval IS 'Track mailing list postings awaiting approval from the team owner.';


COMMENT ON COLUMN public.messageapproval.posted_by IS 'The person who posted the message.';


COMMENT ON COLUMN public.messageapproval.mailing_list IS 'The mailing list to which the message was posted.';


COMMENT ON COLUMN public.messageapproval.posted_message IS 'Foreign key to libraryfilealias table pointing to where the posted message''s text lives.';


COMMENT ON COLUMN public.messageapproval.posted_date IS 'The date the message was posted.';


COMMENT ON COLUMN public.messageapproval.status IS 'The status of the posted message.  Values are described in dbschema.PostedMessageStatus.';


COMMENT ON COLUMN public.messageapproval.disposed_by IS 'The person who disposed of (i.e. approved or rejected) the message, or NULL if no disposition has yet been made.';


COMMENT ON COLUMN public.messageapproval.disposal_date IS 'The date on which this message was disposed, or NULL if no disposition has yet been made.';


COMMENT ON COLUMN public.messageapproval.reason IS 'The reason for the current status if any. This information will be displayed to the end user and mailing list moderators need to be aware of this - not a private whiteboard.';


COMMENT ON COLUMN public.messageapproval.message IS 'Foreign key to message table pointing to the posted message.';


CREATE SEQUENCE public.messageapproval_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.messageapproval_id_seq OWNED BY public.messageapproval.id;


CREATE TABLE public.messagechunk (
    id integer NOT NULL,
    message integer NOT NULL,
    sequence integer NOT NULL,
    content text,
    blob integer,
    fti public.ts2_tsvector,
    CONSTRAINT text_or_content CHECK ((((blob IS NULL) AND (content IS NULL)) OR ((blob IS NULL) <> (content IS NULL))))
)
WITH (fillfactor='100');


COMMENT ON TABLE public.messagechunk IS 'This table stores a single chunk of a possibly multipart message. There will be at least one row in this table for each message. text/* parts are stored in the content column. All other parts are stored in the Librarian and referenced via the blob column. If both content and blob are NULL, then this chunk has been removed (eg. offensive, legal reasons, virus etc.)';


COMMENT ON COLUMN public.messagechunk.sequence IS 'Order of a particular chunk. Chunks are orders in ascending order starting from 1.';


COMMENT ON COLUMN public.messagechunk.content IS 'Text content for this chunk of the message. This content is full text searchable.';


COMMENT ON COLUMN public.messagechunk.blob IS 'Binary content for this chunk of the message.';


CREATE SEQUENCE public.messagechunk_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.messagechunk_id_seq OWNED BY public.messagechunk.id;


CREATE TABLE public.milestone (
    id integer NOT NULL,
    product integer,
    name text NOT NULL,
    distribution integer,
    dateexpected timestamp without time zone,
    active boolean DEFAULT true NOT NULL,
    productseries integer,
    distroseries integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    summary text,
    codename text,
    CONSTRAINT valid_name CHECK (public.valid_name(name)),
    CONSTRAINT valid_target CHECK ((NOT ((product IS NULL) AND (distribution IS NULL))))
);


COMMENT ON TABLE public.milestone IS 'An identifier that helps a maintainer group together things in some way, e.g. "1.2" could be a Milestone that bazaar developers could use to mark a task as needing fixing in bazaar 1.2.';


COMMENT ON COLUMN public.milestone.product IS 'The product for which this is a milestone.';


COMMENT ON COLUMN public.milestone.name IS 'The identifier text, e.g. "1.2."';


COMMENT ON COLUMN public.milestone.distribution IS 'The distribution to which this milestone belongs, if it is a distro milestone.';


COMMENT ON COLUMN public.milestone.dateexpected IS 'If set, the date on which we expect this milestone to be delivered. This allows for optional sorting by date.';


COMMENT ON COLUMN public.milestone.active IS 'Whether or not this milestone should be displayed in general listings. All milestones will be visible on the "page of milestones for product foo", but we want to be able to screen out obviously old milestones over time, for the general listings and vocabularies.';


COMMENT ON COLUMN public.milestone.productseries IS 'The productseries for which this is a milestone. A milestone on a productseries is ALWAYS also a milestone for the same product. This is because milestones started out on products/distributions but are moving to being on series/distroseries.';


COMMENT ON COLUMN public.milestone.distroseries IS 'The distroseries for which this is a milestone. A milestone on a distroseries is ALWAYS also a milestone for the same distribution. This is because milestones started out on products/distributions but are moving to being on series/distroseries.';


COMMENT ON COLUMN public.milestone.summary IS 'This can be used to summarize the changes included in past milestones and to document the status of current milestones.';


COMMENT ON COLUMN public.milestone.codename IS 'A fun or easier to remember name for the milestone/release.';


CREATE SEQUENCE public.milestone_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.milestone_id_seq OWNED BY public.milestone.id;


CREATE TABLE public.milestonetag (
    id integer NOT NULL,
    milestone integer NOT NULL,
    tag text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    created_by integer NOT NULL,
    CONSTRAINT valid_tag CHECK (public.valid_name(tag))
);


COMMENT ON TABLE public.milestonetag IS 'Attaches simple text tags to a milestone.';


COMMENT ON COLUMN public.milestonetag.milestone IS 'The milestone the tag is attached to.';


COMMENT ON COLUMN public.milestonetag.tag IS 'The text representation of the tag.';


CREATE SEQUENCE public.milestonetag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.milestonetag_id_seq OWNED BY public.milestonetag.id;


CREATE TABLE public.mirrorcdimagedistroseries (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    distroseries integer NOT NULL,
    flavour text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.mirrorcdimagedistroseries IS 'The mirror of a given CD/DVD image.';


COMMENT ON COLUMN public.mirrorcdimagedistroseries.distribution_mirror IS 'The distribution mirror.';


COMMENT ON COLUMN public.mirrorcdimagedistroseries.distroseries IS 'The Distribution Release.';


COMMENT ON COLUMN public.mirrorcdimagedistroseries.flavour IS 'The Distribution Release Flavour.';


CREATE SEQUENCE public.mirrorcdimagedistroseries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mirrorcdimagedistroseries_id_seq OWNED BY public.mirrorcdimagedistroseries.id;


CREATE TABLE public.mirrordistroarchseries (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    distroarchseries integer NOT NULL,
    freshness integer NOT NULL,
    pocket integer NOT NULL,
    component integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.mirrordistroarchseries IS 'The mirror of the packages of a given Distro Arch Release.';


COMMENT ON COLUMN public.mirrordistroarchseries.distribution_mirror IS 'The distribution mirror.';


COMMENT ON COLUMN public.mirrordistroarchseries.distroarchseries IS 'The distro arch series.';


COMMENT ON COLUMN public.mirrordistroarchseries.freshness IS 'The freshness of the mirror, that is, how up-to-date it is.';


COMMENT ON COLUMN public.mirrordistroarchseries.pocket IS 'The PackagePublishingPocket.';


CREATE SEQUENCE public.mirrordistroarchseries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mirrordistroarchseries_id_seq OWNED BY public.mirrordistroarchseries.id;


CREATE TABLE public.mirrordistroseriessource (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    distroseries integer NOT NULL,
    freshness integer NOT NULL,
    pocket integer NOT NULL,
    component integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.mirrordistroseriessource IS 'The mirror of a given Distro Release';


COMMENT ON COLUMN public.mirrordistroseriessource.distribution_mirror IS 'The distribution mirror.';


COMMENT ON COLUMN public.mirrordistroseriessource.distroseries IS 'The Distribution Release.';


COMMENT ON COLUMN public.mirrordistroseriessource.freshness IS 'The freshness of the mirror, that is, how up-to-date it is.';


CREATE SEQUENCE public.mirrordistroseriessource_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mirrordistroseriessource_id_seq OWNED BY public.mirrordistroseriessource.id;


CREATE TABLE public.mirrorproberecord (
    id integer NOT NULL,
    distribution_mirror integer NOT NULL,
    log_file integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL
);


COMMENT ON TABLE public.mirrorproberecord IS 'Records stored when a mirror is probed.';


COMMENT ON COLUMN public.mirrorproberecord.distribution_mirror IS 'The DistributionMirror.';


COMMENT ON COLUMN public.mirrorproberecord.log_file IS 'The log file of the probe.';


COMMENT ON COLUMN public.mirrorproberecord.date_created IS 'The date and time the probe was performed.';


CREATE SEQUENCE public.mirrorproberecord_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mirrorproberecord_id_seq OWNED BY public.mirrorproberecord.id;


CREATE TABLE public.nameblacklist (
    id integer NOT NULL,
    regexp text NOT NULL,
    comment text,
    admin integer,
    CONSTRAINT valid_regexp CHECK (public.valid_regexp(regexp))
);


COMMENT ON TABLE public.nameblacklist IS 'A list of regular expressions used to blacklist names.';


COMMENT ON COLUMN public.nameblacklist.regexp IS 'A Python regular expression. It will be compiled with the IGNORECASE, UNICODE and VERBOSE flags. The Python search method will be used rather than match, so ^ markers should be used to indicate the start of a string.';


COMMENT ON COLUMN public.nameblacklist.comment IS 'An optional comment on why this regexp was entered. It should not be displayed to non-admins and its only purpose is documentation.';


COMMENT ON COLUMN public.nameblacklist.admin IS 'The person who can override the blacklisted name.';


CREATE SEQUENCE public.nameblacklist_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.nameblacklist_id_seq OWNED BY public.nameblacklist.id;


CREATE TABLE public.oauthaccesstoken (
    id integer NOT NULL,
    consumer integer NOT NULL,
    person integer NOT NULL,
    permission integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_expires timestamp without time zone,
    key text NOT NULL,
    secret text NOT NULL,
    product integer,
    project integer,
    distribution integer,
    sourcepackagename integer,
    CONSTRAINT just_one_context CHECK ((public.null_count(ARRAY[product, project, distribution]) >= 2)),
    CONSTRAINT sourcepackagename_needs_distro CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);


COMMENT ON TABLE public.oauthaccesstoken IS 'An access token used by the consumer to act on behalf of one of our users.';


COMMENT ON COLUMN public.oauthaccesstoken.consumer IS 'The consumer which is going to access the protected resources.';


COMMENT ON COLUMN public.oauthaccesstoken.person IS 'The person on whose behalf the
consumer will access Launchpad.';


COMMENT ON COLUMN public.oauthaccesstoken.permission IS 'The permission given by that person to the consumer.';


COMMENT ON COLUMN public.oauthaccesstoken.date_created IS 'The date/time in which the token was created.';


COMMENT ON COLUMN public.oauthaccesstoken.date_expires IS 'The date/time in which this token will stop being accepted by Launchpad.';


COMMENT ON COLUMN public.oauthaccesstoken.key IS 'This token''s unique key.';


COMMENT ON COLUMN public.oauthaccesstoken.secret IS 'The secret used by the consumer (together with the token''s key) to access Launchpad on behalf of the person.';


COMMENT ON COLUMN public.oauthaccesstoken.product IS 'The product associated with this token.';


COMMENT ON COLUMN public.oauthaccesstoken.project IS 'The project associated with this token.';


COMMENT ON COLUMN public.oauthaccesstoken.distribution IS 'The distribution associated with this token.';


COMMENT ON COLUMN public.oauthaccesstoken.sourcepackagename IS 'The sourcepackagename associated with this token.';


CREATE SEQUENCE public.oauthaccesstoken_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.oauthaccesstoken_id_seq OWNED BY public.oauthaccesstoken.id;


CREATE TABLE public.oauthconsumer (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    disabled boolean DEFAULT false NOT NULL,
    key text NOT NULL,
    secret text
);


COMMENT ON TABLE public.oauthconsumer IS 'A third part application that will access Launchpad on behalf of one of our users.';


COMMENT ON COLUMN public.oauthconsumer.date_created IS 'The creation date.';


COMMENT ON COLUMN public.oauthconsumer.disabled IS 'Is this consumer disabled?';


COMMENT ON COLUMN public.oauthconsumer.key IS 'The unique key for this consumer.';


COMMENT ON COLUMN public.oauthconsumer.secret IS 'The secret used by this consumer (together with its key) to identify itself with Launchpad.';


CREATE SEQUENCE public.oauthconsumer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.oauthconsumer_id_seq OWNED BY public.oauthconsumer.id;


CREATE TABLE public.oauthrequesttoken (
    id integer NOT NULL,
    consumer integer NOT NULL,
    person integer,
    permission integer,
    date_expires timestamp without time zone,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_reviewed timestamp without time zone,
    key text NOT NULL,
    secret text NOT NULL,
    product integer,
    project integer,
    distribution integer,
    sourcepackagename integer,
    CONSTRAINT just_one_context CHECK ((public.null_count(ARRAY[product, project, distribution]) >= 2)),
    CONSTRAINT reviewed_request CHECK ((((date_reviewed IS NULL) = (person IS NULL)) AND ((date_reviewed IS NULL) = (permission IS NULL)))),
    CONSTRAINT sourcepackagename_needs_distro CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);


COMMENT ON TABLE public.oauthrequesttoken IS 'A request token which, once authorized by the user, is exchanged for an access token.';


COMMENT ON COLUMN public.oauthrequesttoken.consumer IS 'The consumer which is going to access the protected resources.';


COMMENT ON COLUMN public.oauthrequesttoken.person IS 'The person who authorized this token.';


COMMENT ON COLUMN public.oauthrequesttoken.permission IS 'The permission given by the
person to the consumer.';


COMMENT ON COLUMN public.oauthrequesttoken.date_expires IS 'When the authorization is to expire.';


COMMENT ON COLUMN public.oauthrequesttoken.date_created IS 'The date/time in which the token was created.';


COMMENT ON COLUMN public.oauthrequesttoken.date_reviewed IS 'When the authorization request was authorized or rejected by the person.';


COMMENT ON COLUMN public.oauthrequesttoken.key IS 'This token''s unique key.';


COMMENT ON COLUMN public.oauthrequesttoken.secret IS 'The secret used by the consumer (together with the token''s key) to get an access token once the user has authorized its use.';


COMMENT ON COLUMN public.oauthrequesttoken.product IS 'The product associated with this token.';


COMMENT ON COLUMN public.oauthrequesttoken.project IS 'The project associated with this token.';


COMMENT ON COLUMN public.oauthrequesttoken.distribution IS 'The distribution associated with this token.';


COMMENT ON COLUMN public.oauthrequesttoken.sourcepackagename IS 'The sourcepackagename associated with this token.';


CREATE SEQUENCE public.oauthrequesttoken_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.oauthrequesttoken_id_seq OWNED BY public.oauthrequesttoken.id;


CREATE TABLE public.officialbugtag (
    id integer NOT NULL,
    tag text NOT NULL,
    distribution integer,
    project integer,
    product integer,
    CONSTRAINT context_required CHECK (((product IS NOT NULL) OR (distribution IS NOT NULL)))
);


COMMENT ON TABLE public.officialbugtag IS 'Bug tags that have been officially endorced by this product''s or distribution''s lead';


CREATE SEQUENCE public.officialbugtag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.officialbugtag_id_seq OWNED BY public.officialbugtag.id;


CREATE TABLE public.openidconsumerassociation (
    server_url character varying(2047) NOT NULL,
    handle character varying(255) NOT NULL,
    secret bytea,
    issued integer,
    lifetime integer,
    assoc_type character varying(64),
    CONSTRAINT secret_length_constraint CHECK ((length(secret) <= 128))
);


CREATE TABLE public.openidconsumernonce (
    server_url character varying(2047) NOT NULL,
    "timestamp" integer NOT NULL,
    salt character(40) NOT NULL
);


CREATE TABLE public.openididentifier (
    identifier text NOT NULL,
    account integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.openididentifier IS 'OpenId Identifiers that can be used to log into an Account.';


COMMENT ON COLUMN public.openididentifier.identifier IS 'OpenId Identifier. This should be a URL, but is currently just a token that can be used to generate the Identity URL for the Canonical SSO OpenId Provider.';


CREATE TABLE public.packagecopyjob (
    id integer NOT NULL,
    job integer NOT NULL,
    source_archive integer NOT NULL,
    target_archive integer NOT NULL,
    target_distroseries integer,
    job_type integer NOT NULL,
    json_data text,
    package_name text NOT NULL,
    copy_policy integer
);


COMMENT ON TABLE public.packagecopyjob IS 'Contains references to jobs for copying packages between archives.';


COMMENT ON COLUMN public.packagecopyjob.source_archive IS 'The archive from which packages are copied.';


COMMENT ON COLUMN public.packagecopyjob.target_archive IS 'The archive to which packages are copied.';


COMMENT ON COLUMN public.packagecopyjob.target_distroseries IS 'The distroseries to which packages are copied.';


COMMENT ON COLUMN public.packagecopyjob.job_type IS 'The type of job';


COMMENT ON COLUMN public.packagecopyjob.json_data IS 'A JSON struct containing data for the job.';


CREATE SEQUENCE public.packagecopyjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packagecopyjob_id_seq OWNED BY public.packagecopyjob.id;


CREATE TABLE public.packagecopyrequest (
    id integer NOT NULL,
    target_archive integer NOT NULL,
    target_distroseries integer,
    target_component integer,
    target_pocket integer,
    copy_binaries boolean DEFAULT false NOT NULL,
    source_archive integer NOT NULL,
    source_distroseries integer,
    source_component integer,
    source_pocket integer,
    requester integer NOT NULL,
    status integer NOT NULL,
    reason text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_started timestamp without time zone,
    date_completed timestamp without time zone
);


COMMENT ON TABLE public.packagecopyrequest IS 'PackageCopyRequest: A table that captures the status and the details of an inter-archive package copy operation.';


COMMENT ON COLUMN public.packagecopyrequest.target_archive IS 'The archive to which packages will be copied.';


COMMENT ON COLUMN public.packagecopyrequest.target_distroseries IS 'The target distroseries.';


COMMENT ON COLUMN public.packagecopyrequest.target_component IS 'The target component.';


COMMENT ON COLUMN public.packagecopyrequest.target_pocket IS 'The target pocket.';


COMMENT ON COLUMN public.packagecopyrequest.source_archive IS 'The archive from which packages are to be copied.';


COMMENT ON COLUMN public.packagecopyrequest.source_distroseries IS 'The distroseries to which the packages to be copied belong in the source archive.';


COMMENT ON COLUMN public.packagecopyrequest.source_component IS 'The component to which the packages to be copied belong in the source archive.';


COMMENT ON COLUMN public.packagecopyrequest.source_pocket IS 'The pocket for the packages to be copied.';


COMMENT ON COLUMN public.packagecopyrequest.requester IS 'The person who requested the archive operation.';


COMMENT ON COLUMN public.packagecopyrequest.status IS 'Archive operation status, may be one of: new, in-progress, complete, failed, cancelling, cancelled.';


COMMENT ON COLUMN public.packagecopyrequest.reason IS 'The reason why this copy operation was requested.';


COMMENT ON COLUMN public.packagecopyrequest.date_created IS 'Date of creation for this archive operation.';


COMMENT ON COLUMN public.packagecopyrequest.date_started IS 'Start date/time of this archive operation.';


COMMENT ON COLUMN public.packagecopyrequest.date_completed IS 'When did this archive operation conclude?';


CREATE SEQUENCE public.packagecopyrequest_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packagecopyrequest_id_seq OWNED BY public.packagecopyrequest.id;


CREATE TABLE public.packagediff (
    id integer NOT NULL,
    date_requested timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    requester integer,
    from_source integer NOT NULL,
    to_source integer NOT NULL,
    date_fulfilled timestamp without time zone,
    diff_content integer,
    status integer DEFAULT 0 NOT NULL,
    CONSTRAINT distinct_sources CHECK ((from_source <> to_source))
);


COMMENT ON TABLE public.packagediff IS 'This table stores diffs bettwen two scpecific SourcePackageRelease versions.';


COMMENT ON COLUMN public.packagediff.date_requested IS 'Instant when the diff was requested.';


COMMENT ON COLUMN public.packagediff.requester IS 'The Person responsible for the request.';


COMMENT ON COLUMN public.packagediff.from_source IS 'The SourcePackageRelease to diff from.';


COMMENT ON COLUMN public.packagediff.to_source IS 'The SourcePackageRelease to diff to.';


COMMENT ON COLUMN public.packagediff.date_fulfilled IS 'Instant when the diff was completed.';


COMMENT ON COLUMN public.packagediff.diff_content IS 'LibraryFileAlias containing the th diff results.';


COMMENT ON COLUMN public.packagediff.status IS 'Request status, PENDING(0) when created then goes to COMPLETED(1) or FAILED(2), both terminal status where diff_content and date_fulfilled will contain the results of the request.';


CREATE SEQUENCE public.packagediff_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packagediff_id_seq OWNED BY public.packagediff.id;


CREATE TABLE public.packageset (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    owner integer NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    packagesetgroup integer NOT NULL,
    distroseries integer NOT NULL,
    relative_build_score integer DEFAULT 0 NOT NULL,
    CONSTRAINT packageset_name_check CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.packageset IS 'Package sets facilitate the grouping of packages (in a given distro series) for purposes like the control of upload permissions, etc.';


COMMENT ON COLUMN public.packageset.date_created IS 'Date and time of creation.';


COMMENT ON COLUMN public.packageset.owner IS 'The Person or team who owns the package
set group.';


COMMENT ON COLUMN public.packageset.name IS 'The name for the package set on hand.';


COMMENT ON COLUMN public.packageset.description IS 'The description for the package set on hand.';


COMMENT ON COLUMN public.packageset.packagesetgroup IS 'The group this package set is affiliated with.';


COMMENT ON COLUMN public.packageset.distroseries IS 'The distro series this package set belongs to.';


COMMENT ON COLUMN public.packageset.relative_build_score IS 'Build score bonus for packages in this package set.';


CREATE SEQUENCE public.packageset_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packageset_id_seq OWNED BY public.packageset.id;


CREATE TABLE public.packagesetgroup (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    owner integer NOT NULL
);


COMMENT ON TABLE public.packagesetgroup IS 'Package set groups keep track of equivalent package sets across distro series boundaries.';


CREATE SEQUENCE public.packagesetgroup_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packagesetgroup_id_seq OWNED BY public.packagesetgroup.id;


CREATE TABLE public.packagesetinclusion (
    id integer NOT NULL,
    parent integer NOT NULL,
    child integer NOT NULL
);


COMMENT ON TABLE public.packagesetinclusion IS 'sets may form a set-subset hierarchy; this table facilitates the definition of these set-subset relationships.';


COMMENT ON COLUMN public.packagesetinclusion.parent IS 'The package set that is including a subset.';


COMMENT ON COLUMN public.packagesetinclusion.child IS 'The package set that is being included as a subset.';


CREATE SEQUENCE public.packagesetinclusion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packagesetinclusion_id_seq OWNED BY public.packagesetinclusion.id;


CREATE TABLE public.packagesetsources (
    id integer NOT NULL,
    packageset integer NOT NULL,
    sourcepackagename integer NOT NULL
);


COMMENT ON TABLE public.packagesetsources IS 'This table associates package sets and source package names.';


COMMENT ON COLUMN public.packagesetsources.packageset IS 'The associated package set.';


COMMENT ON COLUMN public.packagesetsources.sourcepackagename IS 'The associated source package name.';


CREATE SEQUENCE public.packagesetsources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packagesetsources_id_seq OWNED BY public.packagesetsources.id;


CREATE TABLE public.packageupload (
    id integer NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    distroseries integer NOT NULL,
    pocket integer NOT NULL,
    changesfile integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    signing_key integer,
    archive integer NOT NULL,
    package_copy_job integer,
    searchable_names text NOT NULL,
    searchable_versions text[] NOT NULL,
    signing_key_owner integer,
    signing_key_fingerprint text,
    CONSTRAINT valid_signing_key_fingerprint CHECK (((signing_key_fingerprint IS NULL) OR public.valid_fingerprint(signing_key_fingerprint)))
);


COMMENT ON TABLE public.packageupload IS 'An upload. This table stores information pertaining to uploads to a given DistroSeries/Archive.';


COMMENT ON COLUMN public.packageupload.status IS 'This is an integer field containing the current status of the upload. Possible values are given by the UploadStatus class in dbschema.py';


COMMENT ON COLUMN public.packageupload.distroseries IS 'This integer field refers to the DistroSeries to which this upload is targeted';


COMMENT ON COLUMN public.packageupload.pocket IS 'This is the pocket the upload is targeted at.';


COMMENT ON COLUMN public.packageupload.changesfile IS 'The changes file associated with this upload.';


COMMENT ON COLUMN public.packageupload.archive IS 'The archive to which this upload is targetted.';


CREATE SEQUENCE public.packageupload_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packageupload_id_seq OWNED BY public.packageupload.id;


CREATE TABLE public.packageuploadbuild (
    id integer NOT NULL,
    packageupload integer NOT NULL,
    build integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.packageuploadbuild IS 'An upload binary build. This table stores information pertaining to the builds in a package upload.';


COMMENT ON COLUMN public.packageuploadbuild.packageupload IS 'This integer field refers to the PackageUpload row that this source belongs to.';


COMMENT ON COLUMN public.packageuploadbuild.build IS 'This integer field refers to the Build record related to this upload.';


CREATE SEQUENCE public.packageuploadbuild_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packageuploadbuild_id_seq OWNED BY public.packageuploadbuild.id;


CREATE TABLE public.packageuploadcustom (
    id integer NOT NULL,
    packageupload integer NOT NULL,
    customformat integer NOT NULL,
    libraryfilealias integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.packageuploadcustom IS 'An uploaded custom format file. This table stores information pertaining to the custom upload formats in a package upload.';


COMMENT ON COLUMN public.packageuploadcustom.packageupload IS 'The PackageUpload row this refers to.';


COMMENT ON COLUMN public.packageuploadcustom.customformat IS 'The format of this particular custom uploaded file.';


COMMENT ON COLUMN public.packageuploadcustom.libraryfilealias IS 'The actual file as a librarian alias.';


CREATE SEQUENCE public.packageuploadcustom_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packageuploadcustom_id_seq OWNED BY public.packageuploadcustom.id;


CREATE TABLE public.packageuploadsource (
    id integer NOT NULL,
    packageupload integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.packageuploadsource IS 'Link between an upload and a source package. This table stores information pertaining to the source files in a package upload.';


COMMENT ON COLUMN public.packageuploadsource.packageupload IS 'This integer field refers to the PackageUpload row that this source belongs to.';


COMMENT ON COLUMN public.packageuploadsource.sourcepackagerelease IS 'This integer field refers to the SourcePackageRelease record related to this upload.';


CREATE SEQUENCE public.packageuploadsource_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packageuploadsource_id_seq OWNED BY public.packageuploadsource.id;


CREATE TABLE public.packaging (
    packaging integer NOT NULL,
    id integer DEFAULT nextval(('packaging_id_seq'::text)::regclass) NOT NULL,
    sourcepackagename integer,
    distroseries integer NOT NULL,
    productseries integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    owner integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.packaging IS 'DO NOT JOIN THROUGH THIS TABLE. This is a set
of information linking upstream product series (branches) to distro
packages, but it''s not planned or likely to be complete, in the sense that
we do not attempt to have information for every branch in every derivative
distro managed in Launchpad. So don''t join through this table to get from
product to source package, or vice versa. Rather, use the
ProductSeries.sourcepackages attribute, or the
SourcePackage.productseries attribute. You may need to create a
SourcePackage with a given sourcepackagename and distroseries, then use its
.productrelease attribute. The code behind those methods does more than just
join through the tables, it is also smart enough to look at related
distro''s and parent distroseries, and at Ubuntu in particular.';


COMMENT ON COLUMN public.packaging.packaging IS 'A dbschema Enum (PackagingType)
describing the way the upstream productseries has been packaged. Generally
it will be of type PRIME, meaning that the upstream productseries is the
primary substance of the package, but it might also be INCLUDES, if the
productseries has been included as a statically linked library, for example.
This allows us to say that a given Source Package INCLUDES libneon but is a
PRIME package of tla, for example. By INCLUDES we mean that the code is
actually lumped into the package as ancilliary support material, rather
than simply depending on a separate packaging of that code.';


COMMENT ON COLUMN public.packaging.sourcepackagename IS 'The source package name for
the source package that includes the upstream productseries described in
this Packaging record. There is no requirement that such a sourcepackage
actually be published in the distro.';


COMMENT ON COLUMN public.packaging.distroseries IS 'The distroseries in which the
productseries has been packaged.';


COMMENT ON COLUMN public.packaging.productseries IS 'The upstream product series
that has been packaged in this distroseries sourcepackage.';


COMMENT ON COLUMN public.packaging.owner IS 'This is not the "owner" in the sense
of giving the person any special privileges to edit the Packaging record,
it is simply a record of who told us about this packaging relationship. Note
that we do not keep a history of these, so if someone sets it correctly,
then someone else sets it incorrectly, we lose the first setting.';


CREATE SEQUENCE public.packaging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packaging_id_seq OWNED BY public.packaging.id;


CREATE TABLE public.packagingjob (
    id integer NOT NULL,
    job integer NOT NULL,
    job_type integer NOT NULL,
    productseries integer,
    sourcepackagename integer,
    distroseries integer,
    potemplate integer,
    CONSTRAINT translationtemplatejob_valid_link CHECK ((((((potemplate IS NOT NULL) AND (productseries IS NULL)) AND (distroseries IS NULL)) AND (sourcepackagename IS NULL)) OR ((((potemplate IS NULL) AND (productseries IS NOT NULL)) AND (distroseries IS NOT NULL)) AND (sourcepackagename IS NOT NULL))))
);


COMMENT ON TABLE public.packagingjob IS 'A Job related to a Packaging entry.';


COMMENT ON COLUMN public.packagingjob.job IS 'The Job related to this PackagingJob.';


COMMENT ON COLUMN public.packagingjob.job_type IS 'An enumeration specifying the type of job to perform.';


COMMENT ON COLUMN public.packagingjob.productseries IS 'The productseries of the Packaging.';


COMMENT ON COLUMN public.packagingjob.sourcepackagename IS 'The sourcepackage of the Packaging.';


COMMENT ON COLUMN public.packagingjob.distroseries IS 'The distroseries of the Packaging.';


COMMENT ON COLUMN public.packagingjob.potemplate IS 'A POTemplate to restrict the job to or NULL if all templates need to be handled.';


CREATE SEQUENCE public.packagingjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.packagingjob_id_seq OWNED BY public.packagingjob.id;


CREATE TABLE public.parsedapachelog (
    id integer NOT NULL,
    first_line text NOT NULL,
    bytes_read bigint NOT NULL,
    date_last_parsed timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.parsedapachelog IS 'A parsed apache log file for librarian.';


COMMENT ON COLUMN public.parsedapachelog.first_line IS 'The first line of this log file, smashed to ASCII. This uniquely identifies the log file, even if its filename is changed by log rotation or archival.';


COMMENT ON COLUMN public.parsedapachelog.bytes_read IS 'The number of bytes from this log file that have been parsed.';


CREATE SEQUENCE public.parsedapachelog_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.parsedapachelog_id_seq OWNED BY public.parsedapachelog.id;


CREATE TABLE public.person (
    id integer NOT NULL,
    displayname text NOT NULL,
    teamowner integer,
    teamdescription text,
    name text NOT NULL,
    language integer,
    fti public.ts2_tsvector,
    defaultmembershipperiod integer,
    defaultrenewalperiod integer,
    subscriptionpolicy integer DEFAULT 1 NOT NULL,
    merged integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    homepage_content text,
    icon integer,
    mugshot integer,
    hide_email_addresses boolean DEFAULT false NOT NULL,
    creation_rationale integer,
    creation_comment text,
    registrant integer,
    logo integer,
    renewal_policy integer DEFAULT 10 NOT NULL,
    personal_standing integer DEFAULT 0 NOT NULL,
    personal_standing_reason text,
    mail_resumption_date date,
    mailing_list_auto_subscribe_policy integer DEFAULT 1 NOT NULL,
    mailing_list_receive_duplicates boolean DEFAULT true NOT NULL,
    visibility integer DEFAULT 1 NOT NULL,
    verbose_bugnotifications boolean DEFAULT false NOT NULL,
    account integer,
    description text,
    CONSTRAINT creation_rationale_not_null_for_people CHECK (((creation_rationale IS NULL) = (teamowner IS NOT NULL))),
    CONSTRAINT no_loops CHECK ((id <> teamowner)),
    CONSTRAINT non_empty_displayname CHECK ((btrim(displayname) <> ''::text)),
    CONSTRAINT people_have_no_emblems CHECK (((icon IS NULL) OR (teamowner IS NOT NULL))),
    CONSTRAINT sane_defaultrenewalperiod CHECK (
CASE
    WHEN (teamowner IS NULL) THEN (defaultrenewalperiod IS NULL)
    WHEN (renewal_policy = ANY (ARRAY[20, 30])) THEN ((defaultrenewalperiod IS NOT NULL) AND (defaultrenewalperiod > 0))
    ELSE ((defaultrenewalperiod IS NULL) OR (defaultrenewalperiod > 0))
END),
    CONSTRAINT teams_have_no_account CHECK (((account IS NULL) OR (teamowner IS NULL))),
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.person IS 'A row represents a person if teamowner is NULL, and represents a team if teamowner is set.';


COMMENT ON COLUMN public.person.displayname IS 'Person or group''s name as it should be rendered to screen';


COMMENT ON COLUMN public.person.teamowner IS 'id of the team owner. Team owners will have authority to add or remove people from the team.';


COMMENT ON COLUMN public.person.teamdescription IS 'Informative description of the team. Format and restrictions are as yet undefined.';


COMMENT ON COLUMN public.person.name IS 'Short mneumonic name uniquely identifying this person or team. Useful for url traversal or in places where we need to unambiguously refer to a person or team (as displayname is not unique).';


COMMENT ON COLUMN public.person.language IS 'Preferred language for this person (unset for teams). UI should be displayed in this language wherever possible.';


COMMENT ON COLUMN public.person.subscriptionpolicy IS 'The policy for new members to join this team.';


COMMENT ON COLUMN public.person.homepage_content IS 'A home page for this person in the Launchpad. In short, this is like a personal wiki page. The person will get to edit their own page, and it will be published on /people/foo/. Note that this is in text format, and will migrate to being in Moin format as a sort of mini-wiki-homepage.';


COMMENT ON COLUMN public.person.icon IS 'The library file alias to a small image to be used as an icon whenever we are referring to that person.';


COMMENT ON COLUMN public.person.mugshot IS 'The library file alias of a hackermugshot image to display as the "face" of a person, on their home page.';


COMMENT ON COLUMN public.person.creation_rationale IS 'The rationale for the creation of this person -- a dbschema value.';


COMMENT ON COLUMN public.person.creation_comment IS 'A text comment for the creation of this person.';


COMMENT ON COLUMN public.person.registrant IS 'The user who created this profile.';


COMMENT ON COLUMN public.person.logo IS 'The library file alias of a smaller version of this person''s mugshot.';


COMMENT ON COLUMN public.person.renewal_policy IS 'The policy for membership renewal on this team.';


COMMENT ON COLUMN public.person.personal_standing IS 'The standing of the person, which indicates (for now, just) whether the person can post to a mailing list without requiring first post moderation.  Values are documented in dbschema.PersonalStanding.';


COMMENT ON COLUMN public.person.personal_standing_reason IS 'The reason a person''s standing has changed.';


COMMENT ON COLUMN public.person.mail_resumption_date IS 'A NULL resumption date or a date in the past indicates that there is no vacation in effect.  Vacations are granular to the day, so a datetime is not necessary.';


COMMENT ON COLUMN public.person.mailing_list_auto_subscribe_policy IS 'The auto-subscription policy for the person, i.e. whether and how the user is automatically subscribed to mailing lists for teams they join.  Values are described in dbschema.MailingListAutoSubscribePolicy.';


COMMENT ON COLUMN public.person.mailing_list_receive_duplicates IS 'True means the user wants to receive list copies of messages on which they are explicitly named as a recipient.';


COMMENT ON COLUMN public.person.visibility IS 'person.PersonVisibility enumeration which can be set to Public, Public with Private Membership, or Private.';


COMMENT ON COLUMN public.person.verbose_bugnotifications IS 'If true, all bugnotifications sent to this Person will include the bug description.';


COMMENT ON COLUMN public.person.account IS 'The Account linked to this Person, if there is one.';


CREATE SEQUENCE public.person_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.person_id_seq OWNED BY public.person.id;


CREATE TABLE public.personlanguage (
    id integer NOT NULL,
    person integer NOT NULL,
    language integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.personlanguage IS 'PersonLanguage: This table stores the preferred languages that a Person has, it''s used in Rosetta to select the languages that should be showed to be translated.';


COMMENT ON COLUMN public.personlanguage.person IS 'This field is a reference to a Person object that has this preference.';


COMMENT ON COLUMN public.personlanguage.language IS 'This field is a reference to a Language object that says that the Person associated to this row knows how to translate/understand this language.';


CREATE SEQUENCE public.personlanguage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.personlanguage_id_seq OWNED BY public.personlanguage.id;


CREATE TABLE public.personlocation (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    person integer NOT NULL,
    latitude double precision,
    longitude double precision,
    time_zone text,
    last_modified_by integer NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    visible boolean DEFAULT true,
    locked boolean DEFAULT false,
    CONSTRAINT latitude_and_longitude_together CHECK (((latitude IS NULL) = (longitude IS NULL)))
);


COMMENT ON TABLE public.personlocation IS 'The geographical coordinates and time zone for a person.';


COMMENT ON COLUMN public.personlocation.latitude IS 'The latitude this person has given for their default location.';


COMMENT ON COLUMN public.personlocation.longitude IS 'The longitude this person has given for their default location.';


COMMENT ON COLUMN public.personlocation.time_zone IS 'The name of the time zone this person prefers (if unset, UTC is used).  UI should display dates and times in this time zone wherever possible.';


COMMENT ON COLUMN public.personlocation.last_modified_by IS 'The person who last updated this record. We allow people to provide location and time zone information for other users, when those users have not specified their own location. This allows people to garden the location information for their teams, for example, like a wiki.';


COMMENT ON COLUMN public.personlocation.date_last_modified IS 'The date this record was last modified.';


COMMENT ON COLUMN public.personlocation.visible IS 'Should this person''s location and time zone be visible to others?';


COMMENT ON COLUMN public.personlocation.locked IS 'Whether or not this record can be modified by someone other than the person themselves?';


CREATE SEQUENCE public.personlocation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.personlocation_id_seq OWNED BY public.personlocation.id;


CREATE TABLE public.personnotification (
    id integer NOT NULL,
    person integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_emailed timestamp without time zone,
    body text NOT NULL,
    subject text NOT NULL
);


COMMENT ON TABLE public.personnotification IS 'Notifications to be sent that are related to edits and changes of the details of a specific person or team. Note that these are not keyed against the "person who will be notified", these are notifications "about a person". We use this table to queue up notifications that can then be sent asyncronously - when one user edits information about another person (like the PersonLocation) we want to notify the person concerned that their details have been modified but we do not want to do this during the handling of the form submission. So we store the reminder to notify here, and send it later in a batch. This is modelled on the pattern of BugNotification.';


COMMENT ON COLUMN public.personnotification.person IS 'The Person who has been edited or modified.';


COMMENT ON COLUMN public.personnotification.date_emailed IS 'When this notification was emailed to the relevant people.';


COMMENT ON COLUMN public.personnotification.body IS 'The textual body of the notification to be sent.';


COMMENT ON COLUMN public.personnotification.subject IS 'The subject of the mail to be sent.';


CREATE SEQUENCE public.personnotification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.personnotification_id_seq OWNED BY public.personnotification.id;


CREATE TABLE public.personsettings (
    person integer NOT NULL,
    selfgenerated_bugnotifications boolean DEFAULT false NOT NULL,
    expanded_notification_footers boolean NOT NULL,
    require_strong_email_authentication boolean
);


COMMENT ON TABLE public.personsettings IS 'Flags and settings corresponding to a Person. These are in a separate table to remove infrequently used data from the Person table itself.';


COMMENT ON COLUMN public.personsettings.selfgenerated_bugnotifications IS 'If true, users receive bugnotifications for actions they personally triggered.';


COMMENT ON COLUMN public.personsettings.expanded_notification_footers IS 'Include filtering information in e-mail footers.';


COMMENT ON COLUMN public.personsettings.require_strong_email_authentication IS 'Require strong authentication for incoming emails.';


CREATE TABLE public.persontransferjob (
    id integer NOT NULL,
    job integer NOT NULL,
    job_type integer NOT NULL,
    minor_person integer NOT NULL,
    major_person integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.persontransferjob IS 'Contains references to jobs for adding team members or merging person entries.';


COMMENT ON COLUMN public.persontransferjob.job IS 'A reference to a row in the Job table that has all the common job details.';


COMMENT ON COLUMN public.persontransferjob.job_type IS 'The type of job, like add-member notification or merge persons.';


COMMENT ON COLUMN public.persontransferjob.minor_person IS 'The person that is being added is a new member or being merged into another person.';


COMMENT ON COLUMN public.persontransferjob.major_person IS 'The team receiving a new member or the person that another person is merged into.';


COMMENT ON COLUMN public.persontransferjob.json_data IS 'Data that is specific to the type of job, normally stores text to append to email notifications.';


CREATE SEQUENCE public.persontransferjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.persontransferjob_id_seq OWNED BY public.persontransferjob.id;


CREATE TABLE public.pillarname (
    id integer NOT NULL,
    name text NOT NULL,
    product integer,
    project integer,
    distribution integer,
    active boolean DEFAULT true NOT NULL,
    alias_for integer,
    CONSTRAINT only_one_target CHECK ((public.null_count(ARRAY[product, project, distribution, alias_for]) = 3)),
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.pillarname IS 'A cache of the names of our "Pillar''s" (distribution, product, project) to ensure uniqueness in this shared namespace. This is a materialized view maintained by database triggers.';


COMMENT ON COLUMN public.pillarname.alias_for IS 'An alias for another pillarname. Rows with this column set are not maintained by triggers.';


CREATE SEQUENCE public.pillarname_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pillarname_id_seq OWNED BY public.pillarname.id;


CREATE TABLE public.pocketchroot (
    id integer NOT NULL,
    distroarchseries integer,
    pocket integer NOT NULL,
    chroot integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    image_type integer DEFAULT 0 NOT NULL
);


COMMENT ON TABLE public.pocketchroot IS 'PocketChroots: Which chroot belongs to which pocket of which distroarchseries. Any given pocket of any given distroarchseries needs a specific chroot in order to be built. This table links it all together.';


COMMENT ON COLUMN public.pocketchroot.distroarchseries IS 'Which distroarchseries this chroot applies to.';


COMMENT ON COLUMN public.pocketchroot.pocket IS 'Which pocket of the distroarchseries this chroot applies to. Valid values are specified in dbschema.PackagePublishingPocket';


COMMENT ON COLUMN public.pocketchroot.chroot IS 'The chroot used by the pocket of the distroarchseries.';


COMMENT ON COLUMN public.pocketchroot.image_type IS 'The type of this image.';


CREATE SEQUENCE public.pocketchroot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pocketchroot_id_seq OWNED BY public.pocketchroot.id;


CREATE TABLE public.poexportrequest (
    id integer NOT NULL,
    person integer NOT NULL,
    potemplate integer NOT NULL,
    pofile integer,
    format integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.poexportrequest IS 'A request from a user that a PO template or a PO file be exported
asynchronously.';


COMMENT ON COLUMN public.poexportrequest.person IS 'The person who made the request.';


COMMENT ON COLUMN public.poexportrequest.potemplate IS 'The PO template being requested.';


COMMENT ON COLUMN public.poexportrequest.pofile IS 'The PO file being requested, or NULL.';


COMMENT ON COLUMN public.poexportrequest.format IS 'The format the user would like the export to be in. See the RosettaFileFormat DB schema for possible values.';


CREATE SEQUENCE public.poexportrequest_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.poexportrequest_id_seq OWNED BY public.poexportrequest.id;


CREATE TABLE public.pofile (
    id integer NOT NULL,
    potemplate integer NOT NULL,
    language integer NOT NULL,
    description text,
    topcomment text,
    header text,
    fuzzyheader boolean NOT NULL,
    lasttranslator integer,
    currentcount integer NOT NULL,
    updatescount integer NOT NULL,
    rosettacount integer NOT NULL,
    lastparsed timestamp without time zone,
    owner integer NOT NULL,
    path text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    from_sourcepackagename integer,
    unreviewed_count integer DEFAULT 0 NOT NULL,
    date_changed timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.pofile IS 'This table stores a PO file for a given PO template.';


COMMENT ON COLUMN public.pofile.path IS 'The path (included the filename) inside the tree from where the content was imported.';


COMMENT ON COLUMN public.pofile.from_sourcepackagename IS 'The sourcepackagename from where the last .po file came (only if it''s different from POFile.potemplate.sourcepackagename)';


COMMENT ON COLUMN public.pofile.unreviewed_count IS 'Number of POTMsgSets with new,
unreviewed TranslationMessages for this POFile.';


CREATE SEQUENCE public.pofile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pofile_id_seq OWNED BY public.pofile.id;


CREATE TABLE public.pofilestatsjob (
    job integer NOT NULL,
    pofile integer NOT NULL
);


CREATE TABLE public.pofiletranslator (
    id integer NOT NULL,
    person integer NOT NULL,
    pofile integer NOT NULL,
    date_last_touched timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.pofiletranslator IS 'A materialized view caching who has translated what pofile.';


COMMENT ON COLUMN public.pofiletranslator.person IS 'The person who submitted the translation.';


COMMENT ON COLUMN public.pofiletranslator.pofile IS 'The pofile the translation was submitted for.';


COMMENT ON COLUMN public.pofiletranslator.date_last_touched IS 'When was added latest
translation message.';


CREATE SEQUENCE public.pofiletranslator_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pofiletranslator_id_seq OWNED BY public.pofiletranslator.id;


CREATE TABLE public.poll (
    id integer NOT NULL,
    team integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    dateopens timestamp without time zone NOT NULL,
    datecloses timestamp without time zone NOT NULL,
    proposition text NOT NULL,
    type integer NOT NULL,
    allowspoilt boolean DEFAULT false NOT NULL,
    secrecy integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT sane_dates CHECK ((dateopens < datecloses))
);


COMMENT ON TABLE public.poll IS 'The polls belonging to teams.';


COMMENT ON COLUMN public.poll.team IS 'The team this poll belongs to';


COMMENT ON COLUMN public.poll.name IS 'The unique name of this poll.';


COMMENT ON COLUMN public.poll.title IS 'The title of this poll.';


COMMENT ON COLUMN public.poll.dateopens IS 'The date and time when this poll opens.';


COMMENT ON COLUMN public.poll.datecloses IS 'The date and time when this poll closes.';


COMMENT ON COLUMN public.poll.proposition IS 'The proposition that is going to be voted.';


COMMENT ON COLUMN public.poll.type IS 'The type of this poll (Simple, Preferential, etc).';


COMMENT ON COLUMN public.poll.allowspoilt IS 'If people can spoil their votes.';


COMMENT ON COLUMN public.poll.secrecy IS 'If people votes are SECRET (no one can see), ADMIN (team administrators can see) or PUBLIC (everyone can see).';


CREATE SEQUENCE public.poll_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.poll_id_seq OWNED BY public.poll.id;


CREATE TABLE public.polloption (
    id integer NOT NULL,
    poll integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    active boolean DEFAULT true NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.polloption IS 'The options belonging to polls.';


COMMENT ON COLUMN public.polloption.poll IS 'The poll this options belongs to.';


COMMENT ON COLUMN public.polloption.name IS 'The name of this option.';


COMMENT ON COLUMN public.polloption.title IS 'A short title for this option.';


COMMENT ON COLUMN public.polloption.active IS 'If TRUE, people will be able to vote on this option. Otherwise they don''t.';


CREATE SEQUENCE public.polloption_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.polloption_id_seq OWNED BY public.polloption.id;


CREATE TABLE public.pomsgid (
    id integer NOT NULL,
    msgid text NOT NULL
);


CREATE SEQUENCE public.pomsgid_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pomsgid_id_seq OWNED BY public.pomsgid.id;


CREATE TABLE public.potemplate (
    id integer NOT NULL,
    priority integer DEFAULT 0 NOT NULL,
    description text,
    copyright text,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    path text NOT NULL,
    iscurrent boolean NOT NULL,
    messagecount integer NOT NULL,
    owner integer NOT NULL,
    sourcepackagename integer,
    distroseries integer,
    sourcepackageversion text,
    header text NOT NULL,
    binarypackagename integer,
    languagepack boolean DEFAULT false NOT NULL,
    productseries integer,
    from_sourcepackagename integer,
    date_last_updated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    source_file integer,
    source_file_format integer DEFAULT 1 NOT NULL,
    name text NOT NULL,
    translation_domain text NOT NULL,
    suggestive boolean,
    CONSTRAINT potemplate_valid_name CHECK (public.valid_name(name)),
    CONSTRAINT valid_from_sourcepackagename CHECK (((sourcepackagename IS NOT NULL) OR (from_sourcepackagename IS NULL))),
    CONSTRAINT valid_link CHECK ((((productseries IS NULL) <> (distroseries IS NULL)) AND ((distroseries IS NULL) = (sourcepackagename IS NULL))))
);


COMMENT ON TABLE public.potemplate IS 'This table stores a pot file for a given product.';


COMMENT ON COLUMN public.potemplate.path IS 'The path to the .pot source file inside the tarball tree, including the filename.';


COMMENT ON COLUMN public.potemplate.sourcepackagename IS 'A reference to a sourcepackage name from where this POTemplate comes.';


COMMENT ON COLUMN public.potemplate.distroseries IS 'A reference to the distribution from where this POTemplate comes.';


COMMENT ON COLUMN public.potemplate.sourcepackageversion IS 'The sourcepackage version string from where this potemplate was imported last time with our buildd <-> Rosetta gateway.';


COMMENT ON COLUMN public.potemplate.header IS 'The header of a .pot file when we import it. Most important info from it is POT-Creation-Date and custom headers.';


COMMENT ON COLUMN public.potemplate.productseries IS 'A reference to a ProductSeries from where this POTemplate comes.';


COMMENT ON COLUMN public.potemplate.from_sourcepackagename IS 'The sourcepackagename from where the last .pot file came (only if it''s different from POTemplate.sourcepackagename)';


COMMENT ON COLUMN public.potemplate.source_file IS 'Reference to Librarian file storing the last uploaded template file.';


COMMENT ON COLUMN public.potemplate.source_file_format IS 'File format for the Librarian file referenced in "source_file" column.';


COMMENT ON COLUMN public.potemplate.name IS 'The name of the POTemplate set. It must be unique';


COMMENT ON COLUMN public.potemplate.translation_domain IS 'The translation domain for this POTemplate';


CREATE SEQUENCE public.potemplate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.potemplate_id_seq OWNED BY public.potemplate.id;


CREATE TABLE public.potmsgset (
    id integer NOT NULL,
    msgid_singular integer NOT NULL,
    commenttext text,
    filereferences text,
    sourcecomment text,
    flagscomment text,
    context text,
    msgid_plural integer,
    suggestive boolean
);


COMMENT ON TABLE public.potmsgset IS 'This table is stores a collection of msgids
without their translations and all kind of information associated to that set
of messages that could be found in a potemplate file.';


COMMENT ON COLUMN public.potmsgset.msgid_singular IS 'The singular msgid for this message.';


COMMENT ON COLUMN public.potmsgset.commenttext IS 'The comment text that is associated to this message set.';


COMMENT ON COLUMN public.potmsgset.filereferences IS 'The list of files and their line number where this message set was extracted from.';


COMMENT ON COLUMN public.potmsgset.sourcecomment IS 'The comment that was extracted from the source code.';


COMMENT ON COLUMN public.potmsgset.flagscomment IS 'The flags associated with this set (like c-format).';


COMMENT ON COLUMN public.potmsgset.context IS 'Context uniquely defining a message when there are messages with same primemsgids.';


COMMENT ON COLUMN public.potmsgset.msgid_plural IS 'The plural msgid for this message.';


CREATE SEQUENCE public.potmsgset_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.potmsgset_id_seq OWNED BY public.potmsgset.id;


CREATE TABLE public.potranslation (
    id integer NOT NULL,
    translation text NOT NULL
)
WITH (fillfactor='100');


CREATE SEQUENCE public.potranslation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.potranslation_id_seq OWNED BY public.potranslation.id;


CREATE TABLE public.previewdiff (
    id integer NOT NULL,
    source_revision_id text NOT NULL,
    target_revision_id text NOT NULL,
    dependent_revision_id text,
    diff integer NOT NULL,
    conflicts text,
    branch_merge_proposal integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.previewdiff IS 'Contains information about preview diffs, without duplicating information with BranchMergeProposal.';


COMMENT ON COLUMN public.previewdiff.source_revision_id IS 'The source branch revision_id used to generate this diff.';


COMMENT ON COLUMN public.previewdiff.target_revision_id IS 'The target branch revision_id used to generate this diff.';


COMMENT ON COLUMN public.previewdiff.dependent_revision_id IS 'The dependant branch revision_id used to generate this diff.';


COMMENT ON COLUMN public.previewdiff.diff IS 'The last Diff generated for this PreviewDiff.';


COMMENT ON COLUMN public.previewdiff.conflicts IS 'The text description of any conflicts present.';


CREATE SEQUENCE public.previewdiff_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.previewdiff_id_seq OWNED BY public.previewdiff.id;


CREATE TABLE public.processacceptedbugsjob (
    job integer NOT NULL,
    distroseries integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.processacceptedbugsjob IS 'Contains references to jobs for modifying bugs in response to accepting package uploads.';


COMMENT ON COLUMN public.processacceptedbugsjob.job IS 'The Job related to this ProcessAcceptedBugsJob.';


COMMENT ON COLUMN public.processacceptedbugsjob.distroseries IS 'The DistroSeries of the accepted upload.';


COMMENT ON COLUMN public.processacceptedbugsjob.sourcepackagerelease IS 'The SourcePackageRelease of the accepted upload.';


COMMENT ON COLUMN public.processacceptedbugsjob.json_data IS 'A JSON struct containing data for the job.';


CREATE TABLE public.processor (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    restricted boolean NOT NULL,
    build_by_default boolean DEFAULT false NOT NULL,
    supports_nonvirtualized boolean DEFAULT true NOT NULL,
    supports_virtualized boolean DEFAULT false NOT NULL,
    CONSTRAINT restricted_not_default CHECK (((NOT restricted) OR (NOT build_by_default)))
);


COMMENT ON TABLE public.processor IS 'A single processor for which code might be compiled. For example, i386, P2, P3, P4, Itanium1, Itanium2...';


COMMENT ON COLUMN public.processor.name IS 'The name of this processor, for example, i386, Pentium, P2, P3, P4, Itanium, Itanium2, K7, Athlon, Opteron... it should be short and unique.';


CREATE SEQUENCE public.processor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.processor_id_seq OWNED BY public.processor.id;


CREATE TABLE public.product (
    id integer NOT NULL,
    project integer,
    owner integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
    description text,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    homepageurl text,
    screenshotsurl text,
    wikiurl text,
    listurl text,
    programminglang text,
    downloadurl text,
    lastdoap text,
    sourceforgeproject text,
    freshmeatproject text,
    reviewed boolean DEFAULT false NOT NULL,
    active boolean DEFAULT true NOT NULL,
    fti public.ts2_tsvector,
    autoupdate boolean DEFAULT false NOT NULL,
    translationgroup integer,
    translationpermission integer DEFAULT 1 NOT NULL,
    official_rosetta boolean DEFAULT false NOT NULL,
    official_malone boolean DEFAULT false NOT NULL,
    bug_supervisor integer,
    driver integer,
    bugtracker integer,
    development_focus integer,
    homepage_content text,
    icon integer,
    mugshot integer,
    logo integer,
    official_answers boolean DEFAULT false NOT NULL,
    private_specs boolean DEFAULT false NOT NULL,
    license_info text,
    official_blueprints boolean DEFAULT false NOT NULL,
    enable_bug_expiration boolean DEFAULT false NOT NULL,
    bug_reporting_guidelines text,
    reviewer_whiteboard text,
    license_approved boolean DEFAULT false NOT NULL,
    registrant integer NOT NULL,
    remote_product text,
    translation_focus integer,
    max_bug_heat integer,
    bug_reported_acknowledgement text,
    answers_usage integer DEFAULT 10 NOT NULL,
    blueprints_usage integer DEFAULT 10 NOT NULL,
    translations_usage integer DEFAULT 10 NOT NULL,
    enable_bugfiling_duplicate_search boolean DEFAULT true NOT NULL,
    branch_sharing_policy integer,
    bug_sharing_policy integer,
    specification_sharing_policy integer DEFAULT 1 NOT NULL,
    information_type integer DEFAULT 1 NOT NULL,
    vcs integer,
    access_policies integer[],
    CONSTRAINT only_launchpad_has_expiration CHECK (((enable_bug_expiration IS FALSE) OR (official_malone IS TRUE))),
    CONSTRAINT product__valid_information_type CHECK ((information_type = ANY (ARRAY[1, 5, 6]))),
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.product IS 'Product: a DOAP Product. This table stores core information about an open source product. In Launchpad, anything that can be shipped as a tarball would be a product, and in some cases there might be products for things that never actually ship, depending on the project. For example, most projects will have a ''website'' product, because that allows you to file a Malone bug against the project website. Note that these are not actual product releases, which are stored in the ProductRelease table.';


COMMENT ON COLUMN public.product.project IS 'Every Product belongs to one and only one Project, which is referenced in this column.';


COMMENT ON COLUMN public.product.owner IS 'The Product owner would typically be the person who created this product in Launchpad. But we will encourage the upstream maintainer of a product to become the owner in Launchpad. The Product owner can edit any aspect of the Product, as well as appointing people to specific roles with regard to the Product. Also, the owner can add a new ProductRelease and also edit Rosetta POTemplates associated with this product.';


COMMENT ON COLUMN public.product.summary IS 'A brief summary of the product. This will be displayed in bold at the top of the product page, above the description.';


COMMENT ON COLUMN public.product.description IS 'A detailed description of the product, highlighting primary features of the product that may be of interest to end-users. The description may also include links and other references to useful information on the web about this product. The description will be displayed on the product page, below the product summary.';


COMMENT ON COLUMN public.product.listurl IS 'This is the URL where information about a mailing list for this Product can be found. The URL might point at a web archive or at the page where one can subscribe to the mailing list.';


COMMENT ON COLUMN public.product.programminglang IS 'This field records, in plain text, the name of any significant programming languages used in this product. There are no rules, conventions or restrictions on this field at present, other than basic sanity. Examples might be "Python", "Python, C" and "Java".';


COMMENT ON COLUMN public.product.downloadurl IS 'The download URL for a Product should be the best place to download that product, typically off the relevant Project web site. This should not point at the actual file, but at a web page with download information.';


COMMENT ON COLUMN public.product.lastdoap IS 'This column stores a cached copy of the last DOAP description we saw for this product. See the Project.lastdoap field for more info.';


COMMENT ON COLUMN public.product.sourceforgeproject IS 'The SourceForge project name for this product. This is not unique as SourceForge doesn''t use the same project/product structure as DOAP.';


COMMENT ON COLUMN public.product.freshmeatproject IS 'The FreshMeat project name for this product. This is not unique as FreshMeat does not have the same project/product structure as DOAP';


COMMENT ON COLUMN public.product.reviewed IS 'Whether or not someone at Canonical has reviewed this product.';


COMMENT ON COLUMN public.product.active IS 'Whether or not this product should be considered active.';


COMMENT ON COLUMN public.product.translationgroup IS 'The TranslationGroup that is responsible for translations for this product. Note that the Product may be part of a Project which also has a TranslationGroup, in which case the translators from both the product and project translation group have permission to edit the translations of this product.';


COMMENT ON COLUMN public.product.translationpermission IS 'The level of openness of this product''s translation process. The enum lists different approaches to translation, from the very open (anybody can edit any translation in any language) to the completely closed (only designated translators can make any changes at all).';


COMMENT ON COLUMN public.product.official_rosetta IS 'Whether or not this product upstream uses Rosetta for its official translation team and coordination. This is a useful indicator in terms of whether translations in Rosetta for this upstream will quickly move upstream.';


COMMENT ON COLUMN public.product.official_malone IS 'Whether or not this product upstream uses Malone for an official bug tracker. This is useful to help indicate whether or not people are likely to pick up on bugs registered in Malone.';


COMMENT ON COLUMN public.product.bug_supervisor IS 'Person who is responsible for managing bugs on this product.';


COMMENT ON COLUMN public.product.driver IS 'This is a driver for the overall product. This driver will be able to approve nominations of bugs and specs to any series in the product, including backporting to old stable series. You want the smallest group of "overall drivers" here, because you can add specific drivers to each series individually.';


COMMENT ON COLUMN public.product.development_focus IS 'The product series that is the current focus of development.';


COMMENT ON COLUMN public.product.homepage_content IS 'A home page for this product in the Launchpad.';


COMMENT ON COLUMN public.product.icon IS 'The library file alias to a small image to be used as an icon whenever we are referring to a product.';


COMMENT ON COLUMN public.product.mugshot IS 'The library file alias of a mugshot image to display as the branding of a product, on its home page.';


COMMENT ON COLUMN public.product.logo IS 'The library file alias of a smaller version of this product''s mugshot.';


COMMENT ON COLUMN public.product.official_answers IS 'Whether or not this product upstream uses Answers officialy. This is useful to help indicate whether or not that a question will receive an answer.';


COMMENT ON COLUMN public.product.private_specs IS 'Indicates whether specs filed in this product are automatically marked as private.';


COMMENT ON COLUMN public.product.license_info IS 'Additional information about licenses that are not included in the License enumeration.';


COMMENT ON COLUMN public.product.official_blueprints IS 'Whether or not this product upstream uses Blueprints officially. This is useful to help indicate whether or not the upstream project will be actively watching the blueprints in Launchpad.';


COMMENT ON COLUMN public.product.enable_bug_expiration IS 'Indicates whether automatic bug expiration is enabled.';


COMMENT ON COLUMN public.product.bug_reporting_guidelines IS 'Guidelines to the end user for reporting bugs on this product.';


COMMENT ON COLUMN public.product.reviewer_whiteboard IS 'A whiteboard for Launchpad admins, registry experts and the project owners to capture the state of current issues with the project.';


COMMENT ON COLUMN public.product.license_approved IS 'The Other/Open Source license has been approved by an administrator.';


COMMENT ON COLUMN public.product.registrant IS 'The Product registrant is the Person who created the product in Launchpad.  It is set at creation and is never changed thereafter.';


COMMENT ON COLUMN public.product.remote_product IS 'The ID of this product on its remote bug tracker.';


COMMENT ON COLUMN public.product.translation_focus IS 'The ProductSeries that should get the translation effort focus.';


COMMENT ON COLUMN public.product.max_bug_heat IS 'The highest heat value across bugs for this product.';


COMMENT ON COLUMN public.product.bug_reported_acknowledgement IS 'A message of acknowledgement to display to a bug reporter after they''ve reported a new bug.';


COMMENT ON COLUMN public.product.enable_bugfiling_duplicate_search IS 'Enable/disable a search for posiible duplicates when a bug is filed.';


COMMENT ON COLUMN public.product.information_type IS 'Enum describing what type of information is stored, such as type of private or security related data, and used to determine how to apply an access policy.';


COMMENT ON COLUMN public.product.vcs IS 'An enumeration specifying the default version control system for this project.';


CREATE SEQUENCE public.product_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_id_seq OWNED BY public.product.id;


CREATE TABLE public.productjob (
    id integer NOT NULL,
    job integer NOT NULL,
    job_type integer NOT NULL,
    product integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.productjob IS 'Contains references to jobs for updating projects and sendd notifications.';


COMMENT ON COLUMN public.productjob.job IS 'A reference to a row in the Job table that has all the common job details.';


COMMENT ON COLUMN public.productjob.job_type IS 'The type of job, like 30-day-renewal.';


COMMENT ON COLUMN public.productjob.product IS 'The product that is being updated or the maintainers needs notification.';


COMMENT ON COLUMN public.productjob.json_data IS 'Data that is specific to the job type, such as text for notifications.';


CREATE SEQUENCE public.productjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.productjob_id_seq OWNED BY public.productjob.id;


CREATE TABLE public.productlicense (
    id integer NOT NULL,
    product integer NOT NULL,
    license integer NOT NULL
);


COMMENT ON TABLE public.productlicense IS 'The licenses that cover the software for a product.';


COMMENT ON COLUMN public.productlicense.product IS 'Foreign key to the product that has licenses associated with it.';


COMMENT ON COLUMN public.productlicense.license IS 'An integer referencing a value in the License enumeration in product.py';


CREATE SEQUENCE public.productlicense_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.productlicense_id_seq OWNED BY public.productlicense.id;


CREATE TABLE public.productrelease (
    id integer NOT NULL,
    datereleased timestamp without time zone NOT NULL,
    release_notes text,
    changelog text,
    owner integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    milestone integer NOT NULL
);


COMMENT ON TABLE public.productrelease IS 'A Product Release. This is table stores information about a specific ''upstream'' software release, like Apache 2.0.49 or Evolution 1.5.4.';


COMMENT ON COLUMN public.productrelease.datereleased IS 'The date when this version of the product was released.';


COMMENT ON COLUMN public.productrelease.release_notes IS 'Description of changes in this product release.';


COMMENT ON COLUMN public.productrelease.changelog IS 'Detailed description of changes in this product release.';


COMMENT ON COLUMN public.productrelease.owner IS 'The person who created this product release.';


COMMENT ON COLUMN public.productrelease.datecreated IS 'The timestamp when this product release was created.';


COMMENT ON COLUMN public.productrelease.milestone IS 'The milestone for this product release. This is scheduled to become a NOT NULL column, so every product release will be linked to a unique milestone.';


CREATE SEQUENCE public.productrelease_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.productrelease_id_seq OWNED BY public.productrelease.id;


CREATE TABLE public.productreleasefile (
    productrelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval(('productreleasefile_id_seq'::text)::regclass) NOT NULL,
    description text,
    uploader integer NOT NULL,
    date_uploaded timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    fti public.ts2_tsvector,
    signature integer
);


COMMENT ON TABLE public.productreleasefile IS 'Links a ProductRelease to one or more files in the Librarian.';


COMMENT ON COLUMN public.productreleasefile.productrelease IS 'This is the product release this file is associated with';


COMMENT ON COLUMN public.productreleasefile.libraryfile IS 'This is the librarian entry';


COMMENT ON COLUMN public.productreleasefile.filetype IS 'An enum of what kind of file this is. Code tarballs are marked for special treatment (importing into bzr)';


COMMENT ON COLUMN public.productreleasefile.description IS 'A description of what the file contains';


COMMENT ON COLUMN public.productreleasefile.uploader IS 'The person who uploaded this file.';


COMMENT ON COLUMN public.productreleasefile.date_uploaded IS 'The date this file was uploaded.';


COMMENT ON COLUMN public.productreleasefile.signature IS 'This is the signature of the librarian entry as uploaded by the user.';


CREATE SEQUENCE public.productreleasefile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.productreleasefile_id_seq OWNED BY public.productreleasefile.id;


CREATE TABLE public.productseries (
    id integer NOT NULL,
    product integer NOT NULL,
    name text NOT NULL,
    summary text NOT NULL,
    releasefileglob text,
    releaseverstyle integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    driver integer,
    owner integer NOT NULL,
    status integer DEFAULT 2 NOT NULL,
    translations_autoimport_mode integer DEFAULT 1 NOT NULL,
    branch integer,
    translations_branch integer,
    CONSTRAINT valid_name CHECK (public.valid_name(name)),
    CONSTRAINT valid_releasefileglob CHECK (public.valid_absolute_url(releasefileglob))
);


COMMENT ON TABLE public.productseries IS 'A ProductSeries is a set of product releases that are related to a specific version of the product. Typically, each major release of the product starts a new ProductSeries. These often map to a branch in the revision control system of the project, such as "2_0_STABLE". A few conventional Series names are "head" for releases of the HEAD branch, "1.0" for releases with version numbers like "1.0.0" and "1.0.1".  Each product has at least one ProductSeries';


COMMENT ON COLUMN public.productseries.name IS 'The name of the ProductSeries is like a unix name, it should not contain any spaces and should start with a letter or number. Good examples are "2.0", "3.0", "head" and "development".';


COMMENT ON COLUMN public.productseries.summary IS 'A summary of this Product Series. A good example would include the date the series was initiated and whether this is the current recommended series for people to use. The summary is usually displayed at the top of the page, in bold, just beneath the title and above the description, if there is a description field.';


COMMENT ON COLUMN public.productseries.releasefileglob IS 'A fileglob that lets us
see which URLs are potentially new upstream tarball releases. For example:
http://ftp.gnu.org/gnu/libtool/libtool-1.5.*.gz.';


COMMENT ON COLUMN public.productseries.releaseverstyle IS 'An enum giving the style
of this product series release version numbering system.  The options are
documented in dbschema.UpstreamReleaseVersionStyle.  Most applications use
Gnu style numbering, but there are other alternatives.';


COMMENT ON COLUMN public.productseries.driver IS 'This is a person or team who can approve spes and bugs for implementation or fixing in this specific series. Note that the product drivers and project drivers can also do this for any series in the product or project, so use this only for the specific team responsible for this specific series.';


COMMENT ON COLUMN public.productseries.status IS 'The current status of this productseries.';


COMMENT ON COLUMN public.productseries.translations_autoimport_mode IS 'Level of
translations imports from codehosting branch: None, templates only, templates
and translations. See TranslationsBranchImportMode.';


COMMENT ON COLUMN public.productseries.branch IS 'The branch for this product
series.';


COMMENT ON COLUMN public.productseries.translations_branch IS 'Branch to push translations updates to.';


CREATE SEQUENCE public.productseries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.productseries_id_seq OWNED BY public.productseries.id;


CREATE TABLE public.project (
    id integer NOT NULL,
    owner integer NOT NULL,
    name text NOT NULL,
    displayname text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
    description text NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    homepageurl text,
    wikiurl text,
    lastdoap text,
    sourceforgeproject text,
    freshmeatproject text,
    reviewed boolean DEFAULT false NOT NULL,
    active boolean DEFAULT true NOT NULL,
    fti public.ts2_tsvector,
    translationgroup integer,
    translationpermission integer DEFAULT 1 NOT NULL,
    driver integer,
    bugtracker integer,
    homepage_content text,
    icon integer,
    mugshot integer,
    logo integer,
    bug_reporting_guidelines text,
    reviewer_whiteboard text,
    registrant integer NOT NULL,
    max_bug_heat integer,
    bug_reported_acknowledgement text,
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.project IS 'Project: A DOAP Project. This table is the core of the DOAP section of the Launchpad database. It contains details of a single open source Project and is the anchor point for products, potemplates, and translationefforts.';


COMMENT ON COLUMN public.project.owner IS 'The owner of the project will initially be the person who creates this Project in the system. We will encourage upstream project leaders to take on this role. The Project owner is able to edit the project.';


COMMENT ON COLUMN public.project.name IS 'A short lowercase name uniquely identifying the product. Use cases include being used as a key in URL traversal.';


COMMENT ON COLUMN public.project.summary IS 'A brief summary of this project. This
will be displayed in bold text just above the description and below the
title. It should be a single paragraph of not more than 80 words.';


COMMENT ON COLUMN public.project.description IS 'A detailed description of this
project. This should primarily be focused on the organisational aspects of
the project, such as the people involved and the structures that the project
uses to govern itself. It might refer to the primary products of the project
but the detailed descriptions of those products should be in the
Product.description field, not here. So, for example, useful information
such as the dates the project was started and the way the project
coordinates itself are suitable here.';


COMMENT ON COLUMN public.project.homepageurl IS 'The home page URL of this project. Note that this could well be the home page of the main product of this project as well, if the project is too small to have a separate home page for project and product.';


COMMENT ON COLUMN public.project.wikiurl IS 'This is the URL of a wiki that includes information about the project. It might be a page in a bigger wiki, or it might be the top page of a wiki devoted to this project.';


COMMENT ON COLUMN public.project.lastdoap IS 'This column stores a cached copy of the last DOAP description we saw for this project. We cache the last DOAP fragment for this project because there may be some aspects of it which we are unable to represent in the database (such as multiple homepageurl''s instead of just a single homepageurl) and storing the DOAP file allows us to re-parse it later and recover this information when our database model has been updated appropriately.';


COMMENT ON COLUMN public.project.sourceforgeproject IS 'The SourceForge project name for this project. This is not unique as SourceForge doesn''t use the same project/product structure as DOAP.';


COMMENT ON COLUMN public.project.freshmeatproject IS 'The FreshMeat project name for this project. This is not unique as FreshMeat does not have the same project/product structure as DOAP';


COMMENT ON COLUMN public.project.reviewed IS 'Whether or not someone at Canonical has reviewed this project.';


COMMENT ON COLUMN public.project.active IS 'Whether or not this project should be considered active.';


COMMENT ON COLUMN public.project.translationgroup IS 'The translation group that has permission to edit translations across all products in this project. Note that individual products may have their own translationgroup, in which case those translators will also have permission to edit translations for that product.';


COMMENT ON COLUMN public.project.translationpermission IS 'The level of openness of
this project''s translation process. The enum lists different approaches to
translation, from the very open (anybody can edit any translation in any
language) to the completely closed (only designated translators can make any
changes at all).';


COMMENT ON COLUMN public.project.driver IS 'This person or team has the ability to approve specs as goals for any series in any product in the project. Similarly, this person or team can approve bugs as targets for fixing in any series, or backporting of fixes to any series.';


COMMENT ON COLUMN public.project.homepage_content IS 'A home page for this project in the Launchpad.';


COMMENT ON COLUMN public.project.icon IS 'The library file alias to a small image to be used as an icon whenever we are referring to a project.';


COMMENT ON COLUMN public.project.mugshot IS 'The library file alias of a mugshot image to display as the branding of a project, on its home page.';


COMMENT ON COLUMN public.project.logo IS 'The library file alias of a smaller version of this product''s mugshot.';


COMMENT ON COLUMN public.project.bug_reporting_guidelines IS 'Guidelines to the end user for reporting bugs on products in this project.';


COMMENT ON COLUMN public.project.reviewer_whiteboard IS 'A whiteboard for Launchpad admins, registry experts and the project owners to capture the state of current issues with the project.';


COMMENT ON COLUMN public.project.registrant IS 'The registrant is the Person who created the project in Launchpad.  It is set at creation and is never changed thereafter.';


COMMENT ON COLUMN public.project.max_bug_heat IS 'The highest heat value across bugs for products in this project.';


COMMENT ON COLUMN public.project.bug_reported_acknowledgement IS 'A message of acknowledgement to display to a bug reporter after they''ve reported a new bug.';


CREATE SEQUENCE public.project_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.project_id_seq OWNED BY public.project.id;


CREATE TABLE public.publisherconfig (
    id integer NOT NULL,
    distribution integer NOT NULL,
    root_dir text NOT NULL,
    base_url text NOT NULL,
    copy_base_url text NOT NULL
);


CREATE SEQUENCE public.publisherconfig_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.publisherconfig_id_seq OWNED BY public.publisherconfig.id;


CREATE TABLE public.question (
    id integer NOT NULL,
    owner integer NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    assignee integer,
    answerer integer,
    product integer,
    distribution integer,
    sourcepackagename integer,
    status integer NOT NULL,
    priority integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    datelastquery timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    dateaccepted timestamp without time zone,
    datedue timestamp without time zone,
    datelastresponse timestamp without time zone,
    date_solved timestamp without time zone,
    dateclosed timestamp without time zone,
    whiteboard text,
    fti public.ts2_tsvector,
    answer integer,
    language integer NOT NULL,
    faq integer,
    CONSTRAINT product_or_distro CHECK (((product IS NULL) <> (distribution IS NULL))),
    CONSTRAINT sourcepackagename_needs_distro CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);


COMMENT ON TABLE public.question IS 'A question, or support request, for a distribution or for an application. Such questions are created by end users who need support on a particular feature or package or product.';


COMMENT ON COLUMN public.question.assignee IS 'The person who has been assigned to resolve this question. Note that there is no requirement that every question be assigned somebody. Anybody can chip in to help resolve a question, and if they think they have done so we call them the "answerer".';


COMMENT ON COLUMN public.question.answerer IS 'The person who last claimed to have "solved" this support question, giving a response that the owner believe should be sufficient to close the question. This will move the status of the question to "SOLVED". Note that the only person who can actually set the status to SOLVED is the person who asked the question.';


COMMENT ON COLUMN public.question.product IS 'The upstream product to which this quesiton is related. Note that a quesiton MUST be linked either to a product, or to a distribution.';


COMMENT ON COLUMN public.question.distribution IS 'The distribution for which a question was filed. Note that a request MUST be linked either to a product or a distribution.';


COMMENT ON COLUMN public.question.sourcepackagename IS 'An optional source package name. This only makes sense if the question is bound to a distribution.';


COMMENT ON COLUMN public.question.datelastquery IS 'The date we last saw a comment from the requester (owner).';


COMMENT ON COLUMN public.question.dateaccepted IS 'The date we "confirmed" or "accepted" this question. It is usually set to the date of the first response by someone other than the requester. This allows us to track the time between first request and first response.';


COMMENT ON COLUMN public.question.datedue IS 'The date this question is "due", if such a date can be established. Usually this will be set automatically on the basis of a support contract SLA commitment.';


COMMENT ON COLUMN public.question.datelastresponse IS 'The date we last saw a comment from somebody other than the requester.';


COMMENT ON COLUMN public.question.date_solved IS 'The date this question was last marked as solved by the requester (owner). The requester either found a solution, or accepted an answer from another user.';


COMMENT ON COLUMN public.question.dateclosed IS 'The date the requester marked this question CLOSED.';


COMMENT ON COLUMN public.question.whiteboard IS 'A general status whiteboard. This is a scratch space to which arbitrary data can be added (there is only one constant whiteboard with no history). It is displayed at the top of the question. So its a useful way for projects to add their own semantics or metadata to the Answer Tracker.';


COMMENT ON COLUMN public.question.answer IS 'The QuestionMessage that was accepted by the submitter as the "answer" to the question';


COMMENT ON COLUMN public.question.language IS 'The language of the question''s title and description.';


COMMENT ON COLUMN public.question.faq IS 'The FAQ document that contains the long answer to this question.';


CREATE SEQUENCE public.question_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.question_id_seq OWNED BY public.question.id;


CREATE TABLE public.questionjob (
    id integer NOT NULL,
    job integer NOT NULL,
    job_type integer NOT NULL,
    question integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.questionjob IS 'Contains references to jobs regarding questions.';


COMMENT ON COLUMN public.questionjob.job IS 'A reference to a row in the Job table that has all the common job details.';


COMMENT ON COLUMN public.questionjob.job_type IS 'The type of job, such as new-answer-notification.';


COMMENT ON COLUMN public.questionjob.question IS 'The newly added question message.';


COMMENT ON COLUMN public.questionjob.json_data IS 'Data that is specific to the type of job, normally stores text to append to email notifications.';


CREATE SEQUENCE public.questionjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questionjob_id_seq OWNED BY public.questionjob.id;


CREATE TABLE public.questionmessage (
    id integer NOT NULL,
    question integer NOT NULL,
    message integer NOT NULL,
    action integer NOT NULL,
    new_status integer NOT NULL,
    owner integer NOT NULL
);


COMMENT ON TABLE public.questionmessage IS 'A link between a question and a message. This means that the message will be displayed on the question page.';


COMMENT ON COLUMN public.questionmessage.action IS 'The action on the question that was done with this message. This is a value from the QuestionAction enum.';


COMMENT ON COLUMN public.questionmessage.new_status IS 'The status of the question after this message.';


COMMENT ON COLUMN public.questionmessage.owner IS 'Denormalised owner from Message, used for efficient queries on commentors.';


CREATE SEQUENCE public.questionmessage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questionmessage_id_seq OWNED BY public.questionmessage.id;


CREATE TABLE public.questionreopening (
    id integer NOT NULL,
    question integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    reopener integer NOT NULL,
    answerer integer,
    date_solved timestamp without time zone,
    priorstate integer NOT NULL
);


COMMENT ON TABLE public.questionreopening IS 'A record of the times when a question was re-opened. In each case we store the time that it happened, the person who did it, and the person who had previously answered / rejected the question.';


COMMENT ON COLUMN public.questionreopening.reopener IS 'The person who reopened the question.';


COMMENT ON COLUMN public.questionreopening.answerer IS 'The person who was previously listed as the answerer of the question.';


COMMENT ON COLUMN public.questionreopening.priorstate IS 'The state of the question before it was reopened. You can reopen a question that is ANSWERED, or CLOSED, or REJECTED.';


CREATE SEQUENCE public.questionreopening_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questionreopening_id_seq OWNED BY public.questionreopening.id;


CREATE TABLE public.questionsubscription (
    id integer NOT NULL,
    question integer NOT NULL,
    person integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.questionsubscription IS 'A subscription of a person to a particular question.';


CREATE SEQUENCE public.questionsubscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questionsubscription_id_seq OWNED BY public.questionsubscription.id;


CREATE TABLE public.revision (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    log_body text NOT NULL,
    revision_author integer NOT NULL,
    gpgkey integer,
    revision_id text NOT NULL,
    revision_date timestamp without time zone,
    karma_allocated boolean DEFAULT false,
    signing_key_owner integer,
    signing_key_fingerprint text,
    CONSTRAINT valid_signing_key_fingerprint CHECK (((signing_key_fingerprint IS NULL) OR public.valid_fingerprint(signing_key_fingerprint)))
);


CREATE SEQUENCE public.revision_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.revision_id_seq OWNED BY public.revision.id;


CREATE TABLE public.revisionauthor (
    id integer NOT NULL,
    name text NOT NULL,
    email text,
    person integer
);


COMMENT ON TABLE public.revisionauthor IS 'All distinct authors for revisions.';


COMMENT ON COLUMN public.revisionauthor.name IS 'The exact text extracted from the branch revision.';


COMMENT ON COLUMN public.revisionauthor.email IS 'A valid email address extracted from the name.  This email address may or may not be associated with a Launchpad user at this stage.';


COMMENT ON COLUMN public.revisionauthor.person IS 'The Launchpad person that has a verified email address that matches the email address of the revision author.';


CREATE SEQUENCE public.revisionauthor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.revisionauthor_id_seq OWNED BY public.revisionauthor.id;


CREATE TABLE public.revisioncache (
    id integer NOT NULL,
    revision integer NOT NULL,
    revision_author integer NOT NULL,
    revision_date timestamp without time zone NOT NULL,
    product integer,
    distroseries integer,
    sourcepackagename integer,
    private boolean NOT NULL,
    CONSTRAINT valid_target CHECK ((((distroseries IS NULL) = (sourcepackagename IS NULL)) AND (((distroseries IS NULL) AND (product IS NULL)) OR ((distroseries IS NULL) <> (product IS NULL)))))
);


COMMENT ON TABLE public.revisioncache IS 'A cache of revisions where the revision date is in the last 30 days.';


COMMENT ON COLUMN public.revisioncache.revision IS 'A reference to the actual revision.';


COMMENT ON COLUMN public.revisioncache.revision_author IS 'A refernce to the revision author for the revision.';


COMMENT ON COLUMN public.revisioncache.revision_date IS 'The date the revision was made.  Should be within 30 days of today (or the cleanup code is not cleaning up).';


COMMENT ON COLUMN public.revisioncache.product IS 'The product that the revision is found in (if it is indeed in a particular product).';


COMMENT ON COLUMN public.revisioncache.distroseries IS 'The distroseries for which a source package branch contains the revision.';


COMMENT ON COLUMN public.revisioncache.sourcepackagename IS 'The sourcepackagename for which a source package branch contains the revision.';


COMMENT ON COLUMN public.revisioncache.private IS 'True if the revision is only found in private branches, False if it can be found in a non-private branch.';


CREATE SEQUENCE public.revisioncache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.revisioncache_id_seq OWNED BY public.revisioncache.id;


CREATE TABLE public.revisionparent (
    id integer NOT NULL,
    sequence integer NOT NULL,
    revision integer NOT NULL,
    parent_id text NOT NULL
);


CREATE SEQUENCE public.revisionparent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.revisionparent_id_seq OWNED BY public.revisionparent.id;


CREATE TABLE public.revisionproperty (
    id integer NOT NULL,
    revision integer NOT NULL,
    name text NOT NULL,
    value text NOT NULL
);


COMMENT ON TABLE public.revisionproperty IS 'A collection of name and value pairs that appear on a revision.';


COMMENT ON COLUMN public.revisionproperty.revision IS 'The revision which has properties.';


COMMENT ON COLUMN public.revisionproperty.name IS 'The name of the property.';


COMMENT ON COLUMN public.revisionproperty.value IS 'The value of the property.';


CREATE SEQUENCE public.revisionproperty_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.revisionproperty_id_seq OWNED BY public.revisionproperty.id;


CREATE TABLE public.scriptactivity (
    id integer NOT NULL,
    name text NOT NULL,
    hostname text NOT NULL,
    date_started timestamp without time zone NOT NULL,
    date_completed timestamp without time zone NOT NULL
);


COMMENT ON TABLE public.scriptactivity IS 'Records of successful runs of scripts ';


COMMENT ON COLUMN public.scriptactivity.name IS 'The name of the script';


COMMENT ON COLUMN public.scriptactivity.hostname IS 'The hostname of the machine where the script was run';


COMMENT ON COLUMN public.scriptactivity.date_started IS 'The date at which the script started';


COMMENT ON COLUMN public.scriptactivity.date_completed IS 'The date at which the script completed';


CREATE SEQUENCE public.scriptactivity_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.scriptactivity_id_seq OWNED BY public.scriptactivity.id;


CREATE TABLE public.section (
    id integer NOT NULL,
    name text NOT NULL
);


COMMENT ON TABLE public.section IS 'Known sections in Launchpad';


COMMENT ON COLUMN public.section.name IS 'Section name text';


CREATE SEQUENCE public.section_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.section_id_seq OWNED BY public.section.id;


CREATE TABLE public.sectionselection (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    section integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.sectionselection IS 'Allowed sections in a given distroseries.';


COMMENT ON COLUMN public.sectionselection.distroseries IS 'Refers to the distroseries in question.';


COMMENT ON COLUMN public.sectionselection.section IS 'Refers to the section in question.';


CREATE SEQUENCE public.sectionselection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sectionselection_id_seq OWNED BY public.sectionselection.id;


CREATE TABLE public.seriessourcepackagebranch (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    pocket integer NOT NULL,
    sourcepackagename integer NOT NULL,
    branch integer NOT NULL,
    registrant integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.seriessourcepackagebranch IS 'Link between branches and distribution suite.';


COMMENT ON COLUMN public.seriessourcepackagebranch.distroseries IS 'The distroseries the branch is linked to.';


COMMENT ON COLUMN public.seriessourcepackagebranch.pocket IS 'The pocket the branch is linked to.';


COMMENT ON COLUMN public.seriessourcepackagebranch.sourcepackagename IS 'The sourcepackagename the branch is linked to.';


COMMENT ON COLUMN public.seriessourcepackagebranch.branch IS 'The branch being linked to a distribution suite.';


COMMENT ON COLUMN public.seriessourcepackagebranch.registrant IS 'The person who registered this link.';


COMMENT ON COLUMN public.seriessourcepackagebranch.date_created IS 'The date this link was created.';


CREATE SEQUENCE public.seriessourcepackagebranch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seriessourcepackagebranch_id_seq OWNED BY public.seriessourcepackagebranch.id;


CREATE TABLE public.sharingjob (
    id integer NOT NULL,
    job integer NOT NULL,
    product integer,
    distro integer,
    grantee integer,
    job_type integer NOT NULL,
    json_data text
);


COMMENT ON TABLE public.sharingjob IS 'Contains references to jobs that are executed for sharing.';


COMMENT ON COLUMN public.sharingjob.job IS 'A reference to a row in the Job table that has all the common job details.';


COMMENT ON COLUMN public.sharingjob.product IS 'The product that this job is for.';


COMMENT ON COLUMN public.sharingjob.distro IS 'The distro that this job is for.';


COMMENT ON COLUMN public.sharingjob.grantee IS 'The grantee that this job is for.';


COMMENT ON COLUMN public.sharingjob.job_type IS 'The type of job, like remove subscriptions, email users.';


COMMENT ON COLUMN public.sharingjob.json_data IS 'Data that is specific to the type of job.';


CREATE SEQUENCE public.sharingjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sharingjob_id_seq OWNED BY public.sharingjob.id;


CREATE TABLE public.signedcodeofconduct (
    id integer NOT NULL,
    owner integer NOT NULL,
    signingkey integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    signedcode text,
    recipient integer,
    active boolean DEFAULT false NOT NULL,
    admincomment text,
    signing_key_fingerprint text,
    CONSTRAINT valid_signing_key_fingerprint CHECK (((signing_key_fingerprint IS NULL) OR public.valid_fingerprint(signing_key_fingerprint)))
);


CREATE SEQUENCE public.signedcodeofconduct_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.signedcodeofconduct_id_seq OWNED BY public.signedcodeofconduct.id;


CREATE TABLE public.snap (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    owner integer NOT NULL,
    distro_series integer,
    name text NOT NULL,
    description text,
    branch integer,
    git_repository integer,
    git_path text,
    require_virtualized boolean DEFAULT true NOT NULL,
    private boolean DEFAULT false NOT NULL,
    store_upload boolean DEFAULT false NOT NULL,
    store_series integer,
    store_name text,
    store_secrets text,
    auto_build boolean DEFAULT false NOT NULL,
    auto_build_archive integer,
    auto_build_pocket integer,
    is_stale boolean DEFAULT true NOT NULL,
    store_channels text,
    git_repository_url text,
    auto_build_channels text,
    allow_internet boolean DEFAULT true NOT NULL,
    build_source_tarball boolean DEFAULT false NOT NULL,
    CONSTRAINT consistent_auto_build CHECK (((NOT auto_build) OR ((auto_build_archive IS NOT NULL) AND (auto_build_pocket IS NOT NULL)))),
    CONSTRAINT consistent_git_ref CHECK ((((git_repository IS NULL) AND (git_repository_url IS NULL)) = (git_path IS NULL))),
    CONSTRAINT consistent_store_upload CHECK (((NOT store_upload) OR ((store_series IS NOT NULL) AND (store_name IS NOT NULL)))),
    CONSTRAINT consistent_vcs CHECK ((public.null_count(ARRAY[branch, git_repository, octet_length(git_repository_url)]) >= 2)),
    CONSTRAINT valid_git_repository_url CHECK (public.valid_absolute_url(git_repository_url)),
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.snap IS 'A snap package.';


COMMENT ON COLUMN public.snap.registrant IS 'The user who registered the snap package.';


COMMENT ON COLUMN public.snap.owner IS 'The owner of the snap package.';


COMMENT ON COLUMN public.snap.distro_series IS 'The DistroSeries for which the snap package should be built.';


COMMENT ON COLUMN public.snap.name IS 'The name of the snap package, unique per owner and DistroSeries.';


COMMENT ON COLUMN public.snap.description IS 'A description of the snap package.';


COMMENT ON COLUMN public.snap.branch IS 'A Bazaar branch containing a snap recipe.';


COMMENT ON COLUMN public.snap.git_repository IS 'A Git repository with a branch containing a snap recipe.';


COMMENT ON COLUMN public.snap.git_path IS 'The path of the Git branch containing a snap recipe.';


COMMENT ON COLUMN public.snap.require_virtualized IS 'If True, this snap package must be built only on a virtual machine.';


COMMENT ON COLUMN public.snap.private IS 'Whether or not this snap is private.';


COMMENT ON COLUMN public.snap.store_upload IS 'Whether builds of this snap package are automatically uploaded to the store.';


COMMENT ON COLUMN public.snap.store_series IS 'The series in which this snap package should be published in the store.';


COMMENT ON COLUMN public.snap.store_name IS 'The registered name of this snap package in the store.';


COMMENT ON COLUMN public.snap.store_secrets IS 'Serialized secrets issued by the store and the login service to authorize uploads of this snap package.';


COMMENT ON COLUMN public.snap.auto_build IS 'Whether this snap is built automatically when the branch containing its snap recipe changes.';


COMMENT ON COLUMN public.snap.auto_build_archive IS 'The archive that automatic builds of this snap package should build from.';


COMMENT ON COLUMN public.snap.auto_build_pocket IS 'The pocket that automatic builds of this snap package should build from.';


COMMENT ON COLUMN public.snap.is_stale IS 'True if this snap package has not been built since a branch was updated.';


COMMENT ON COLUMN public.snap.store_channels IS 'Channels to release this snap package to after uploading it to the store.';


COMMENT ON COLUMN public.snap.git_repository_url IS 'A URL to a Git repository with a branch containing a snap recipe.';


COMMENT ON COLUMN public.snap.auto_build_channels IS 'A dictionary mapping snap names to channels to use when building this snap package.';


COMMENT ON COLUMN public.snap.allow_internet IS 'If True, builds of this snap may allow access to external network resources.';


COMMENT ON COLUMN public.snap.build_source_tarball IS 'If true, builds of this snap should also build a tarball containing all source code, including external dependencies.';


CREATE SEQUENCE public.snap_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.snap_id_seq OWNED BY public.snap.id;


CREATE TABLE public.snaparch (
    snap integer NOT NULL,
    processor integer NOT NULL
);


COMMENT ON TABLE public.snaparch IS 'The architectures a snap package should be built for.';


COMMENT ON COLUMN public.snaparch.snap IS 'The snap package for which an architecture is specified.';


COMMENT ON COLUMN public.snaparch.processor IS 'The architecture for which the snap package should be built.';


CREATE TABLE public.snapbase (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    name text NOT NULL,
    display_name text NOT NULL,
    distro_series integer NOT NULL,
    build_channels text NOT NULL,
    is_default boolean NOT NULL,
    CONSTRAINT valid_name CHECK (public.valid_name(name))
);


COMMENT ON TABLE public.snapbase IS 'A base for snaps.';


COMMENT ON COLUMN public.snapbase.date_created IS 'The date on which this base was created in Launchpad.';


COMMENT ON COLUMN public.snapbase.registrant IS 'The user who registered this base.';


COMMENT ON COLUMN public.snapbase.name IS 'The unique name of this base.';


COMMENT ON COLUMN public.snapbase.display_name IS 'The display name of this base.';


COMMENT ON COLUMN public.snapbase.distro_series IS 'The distro series used for snap builds that specify this base.';


COMMENT ON COLUMN public.snapbase.build_channels IS 'A dictionary mapping snap names to channels to use when building snaps that specify this base.';


COMMENT ON COLUMN public.snapbase.is_default IS 'Whether this base is the default for snaps that do not specify a base.';


CREATE SEQUENCE public.snapbase_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.snapbase_id_seq OWNED BY public.snapbase.id;


CREATE TABLE public.snapbuild (
    id integer NOT NULL,
    requester integer NOT NULL,
    snap integer NOT NULL,
    archive integer NOT NULL,
    distro_arch_series integer NOT NULL,
    pocket integer NOT NULL,
    processor integer NOT NULL,
    virtualized boolean NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_started timestamp without time zone,
    date_finished timestamp without time zone,
    date_first_dispatched timestamp without time zone,
    builder integer,
    status integer NOT NULL,
    log integer,
    upload_log integer,
    dependencies text,
    failure_count integer DEFAULT 0 NOT NULL,
    build_farm_job integer NOT NULL,
    revision_id text,
    channels text,
    build_request integer,
    store_upload_json_data text
);


COMMENT ON TABLE public.snapbuild IS 'A build record for a snap package.';


COMMENT ON COLUMN public.snapbuild.requester IS 'The person who requested this snap package build.';


COMMENT ON COLUMN public.snapbuild.snap IS 'The snap package to build.';


COMMENT ON COLUMN public.snapbuild.archive IS 'The archive that the snap package should build from.';


COMMENT ON COLUMN public.snapbuild.distro_arch_series IS 'The distroarchseries that the snap package should build from.';


COMMENT ON COLUMN public.snapbuild.pocket IS 'The pocket that the snap package should build from.';


COMMENT ON COLUMN public.snapbuild.virtualized IS 'The virtualization setting required by this build farm job.';


COMMENT ON COLUMN public.snapbuild.date_created IS 'When the build farm job record was created.';


COMMENT ON COLUMN public.snapbuild.date_started IS 'When the build farm job started being processed.';


COMMENT ON COLUMN public.snapbuild.date_finished IS 'When the build farm job finished being processed.';


COMMENT ON COLUMN public.snapbuild.date_first_dispatched IS 'The instant the build was dispatched the first time.  This value will not get overridden if the build is retried.';


COMMENT ON COLUMN public.snapbuild.builder IS 'The builder which processed this build farm job.';


COMMENT ON COLUMN public.snapbuild.status IS 'The current build status.';


COMMENT ON COLUMN public.snapbuild.log IS 'The log file for this build farm job stored in the librarian.';


COMMENT ON COLUMN public.snapbuild.upload_log IS 'The upload log file for this build farm job stored in the librarian.';


COMMENT ON COLUMN public.snapbuild.dependencies IS 'A Debian-like dependency line specifying the current missing dependencies for this build.';


COMMENT ON COLUMN public.snapbuild.failure_count IS 'The number of consecutive failures on this job.  If excessive, the job may be terminated.';


COMMENT ON COLUMN public.snapbuild.build_farm_job IS 'The build farm job with the base information.';


COMMENT ON COLUMN public.snapbuild.revision_id IS 'The revision ID of the branch used for this build, if available.';


COMMENT ON COLUMN public.snapbuild.channels IS 'A dictionary mapping snap names to channels to use for this build.';


COMMENT ON COLUMN public.snapbuild.build_request IS 'The build request that caused this build to be created.';


COMMENT ON COLUMN public.snapbuild.store_upload_json_data IS 'Data that is related to the process of uploading a build to the store.';


CREATE SEQUENCE public.snapbuild_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.snapbuild_id_seq OWNED BY public.snapbuild.id;


CREATE TABLE public.snapbuildjob (
    job integer NOT NULL,
    snapbuild integer NOT NULL,
    job_type integer NOT NULL,
    json_data text NOT NULL
);


COMMENT ON TABLE public.snapbuildjob IS 'Contains references to jobs that are executed for a build of a snap package.';


COMMENT ON COLUMN public.snapbuildjob.job IS 'A reference to a Job row that has all the common job details.';


COMMENT ON COLUMN public.snapbuildjob.snapbuild IS 'The snap build that this job is for.';


COMMENT ON COLUMN public.snapbuildjob.job_type IS 'The type of a job, such as a store upload.';


COMMENT ON COLUMN public.snapbuildjob.json_data IS 'Data that is specific to a particular job type.';


CREATE TABLE public.snapfile (
    id integer NOT NULL,
    snapbuild integer NOT NULL,
    libraryfile integer NOT NULL
);


COMMENT ON TABLE public.snapfile IS 'A link between a snap package build and a file in the librarian that it produces.';


COMMENT ON COLUMN public.snapfile.snapbuild IS 'The snap package build producing this file.';


COMMENT ON COLUMN public.snapfile.libraryfile IS 'A file in the librarian.';


CREATE SEQUENCE public.snapfile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.snapfile_id_seq OWNED BY public.snapfile.id;


CREATE TABLE public.snapjob (
    job integer NOT NULL,
    snap integer NOT NULL,
    job_type integer NOT NULL,
    json_data text NOT NULL
);


COMMENT ON TABLE public.snapjob IS 'Contains references to jobs that are executed for a snap package.';


COMMENT ON COLUMN public.snapjob.job IS 'A reference to a Job row that has all the common job details.';


COMMENT ON COLUMN public.snapjob.snap IS 'The snap package that this job is for.';


COMMENT ON COLUMN public.snapjob.job_type IS 'The type of a job, such as a build request.';


COMMENT ON COLUMN public.snapjob.json_data IS 'Data that is specific to a particular job type.';


CREATE TABLE public.snappydistroseries (
    snappy_series integer NOT NULL,
    distro_series integer,
    preferred boolean DEFAULT false NOT NULL,
    id integer NOT NULL
);


COMMENT ON TABLE public.snappydistroseries IS 'A record indicating that a particular snappy series is valid for builds from a particular distribution series.';


COMMENT ON COLUMN public.snappydistroseries.snappy_series IS 'The snappy series which is valid for builds from this distribution series.';


COMMENT ON COLUMN public.snappydistroseries.distro_series IS 'The distribution series whose builds are valid for this snappy series.';


COMMENT ON COLUMN public.snappydistroseries.preferred IS 'True if this record identifies the default distribution series for builds for this snappy series.';


CREATE SEQUENCE public.snappydistroseries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.snappydistroseries_id_seq OWNED BY public.snappydistroseries.id;


CREATE TABLE public.snappyseries (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    name text NOT NULL,
    display_name text NOT NULL,
    status integer NOT NULL
);


COMMENT ON TABLE public.snappyseries IS 'A series for snap packages in the store.';


COMMENT ON COLUMN public.snappyseries.date_created IS 'The date on which this series was created in Launchpad.';


COMMENT ON COLUMN public.snappyseries.registrant IS 'The user who registered this series.';


COMMENT ON COLUMN public.snappyseries.name IS 'The unique name of this series.';


COMMENT ON COLUMN public.snappyseries.display_name IS 'The display name of this series.';


COMMENT ON COLUMN public.snappyseries.status IS 'The current status of this series.';


CREATE SEQUENCE public.snappyseries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.snappyseries_id_seq OWNED BY public.snappyseries.id;


CREATE TABLE public.sourcepackageformatselection (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    format integer NOT NULL
);


COMMENT ON TABLE public.sourcepackageformatselection IS 'Allowed source package formats for a given distroseries.';


COMMENT ON COLUMN public.sourcepackageformatselection.distroseries IS 'Refers to the distroseries in question.';


COMMENT ON COLUMN public.sourcepackageformatselection.format IS 'The SourcePackageFormat to allow.';


CREATE SEQUENCE public.sourcepackageformatselection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackageformatselection_id_seq OWNED BY public.sourcepackageformatselection.id;


CREATE SEQUENCE public.sourcepackagename_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackagename_id_seq OWNED BY public.sourcepackagename.id;


CREATE TABLE public.sourcepackagepublishinghistory (
    id integer NOT NULL,
    sourcepackagerelease integer NOT NULL,
    distroseries integer NOT NULL,
    status integer NOT NULL,
    component integer NOT NULL,
    section integer NOT NULL,
    datecreated timestamp without time zone NOT NULL,
    datepublished timestamp without time zone,
    datesuperseded timestamp without time zone,
    supersededby integer,
    datemadepending timestamp without time zone,
    scheduleddeletiondate timestamp without time zone,
    dateremoved timestamp without time zone,
    pocket integer DEFAULT 0 NOT NULL,
    archive integer NOT NULL,
    removed_by integer,
    removal_comment text,
    ancestor integer,
    sourcepackagename integer NOT NULL,
    creator integer,
    sponsor integer,
    packageupload integer
);


COMMENT ON TABLE public.sourcepackagepublishinghistory IS 'SourcePackagePublishingHistory: The history of a SourcePackagePublishing record. This table represents the lifetime of a publishing record from inception to deletion. Records are never removed from here and in time the publishing table may become a view onto this table. A column being NULL indicates there''s no data for that state transition. E.g. a package which is removed without being superseded won''t have datesuperseded or supersededby filled in.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.sourcepackagerelease IS 'The sourcepackagerelease being published.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.distroseries IS 'The distroseries into which the sourcepackagerelease is being published.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.status IS 'The current status of the publishing.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.component IS 'The component into which the publishing takes place.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.section IS 'The section into which the publishing takes place.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.datecreated IS 'The date/time on which the publishing record was created.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.datepublished IS 'The date/time on which the source was actually published into an archive.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.datesuperseded IS 'The date/time on which the source was superseded by a new source.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.supersededby IS 'The source which superseded this one.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.datemadepending IS 'The date/time on which this publishing record was made to be pending removal from the archive.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.scheduleddeletiondate IS 'The date/time at which the source is/was scheduled to be deleted.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.dateremoved IS 'The date/time at which the source was actually deleted.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.pocket IS 'The pocket into which this record is published. The RELEASE pocket (zero) provides behaviour as normal. Other pockets may append things to the distroseries name such as the UPDATES pocket (-updates), the SECURITY pocket (-security) and the PROPOSED pocket (-proposed)';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.archive IS 'The target archive for this publishing record.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.removed_by IS 'Person responsible for the removal.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.removal_comment IS 'Reason why the publication was removed.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.ancestor IS 'The source package record published immediately before this one.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.sourcepackagename IS 'Reference to a SourcePackageName.';


COMMENT ON COLUMN public.sourcepackagepublishinghistory.packageupload IS 'The PackageUpload that caused this publication to be created.';


CREATE SEQUENCE public.sourcepackagepublishinghistory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackagepublishinghistory_id_seq OWNED BY public.sourcepackagepublishinghistory.id;


CREATE TABLE public.sourcepackagerecipe (
    id integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL,
    owner integer NOT NULL,
    name text NOT NULL,
    description text,
    build_daily boolean DEFAULT false NOT NULL,
    daily_build_archive integer,
    is_stale boolean DEFAULT true NOT NULL
);


COMMENT ON TABLE public.sourcepackagerecipe IS 'A recipe for assembling a source package from branches.';


COMMENT ON COLUMN public.sourcepackagerecipe.registrant IS 'The person who created this recipe.';


COMMENT ON COLUMN public.sourcepackagerecipe.owner IS 'The person or team who can edit this recipe.';


COMMENT ON COLUMN public.sourcepackagerecipe.name IS 'The name of the recipe in the web/URL.';


COMMENT ON COLUMN public.sourcepackagerecipe.build_daily IS 'If true, this recipe should be built daily.';


COMMENT ON COLUMN public.sourcepackagerecipe.daily_build_archive IS 'The archive to build into for daily builds.';


COMMENT ON COLUMN public.sourcepackagerecipe.is_stale IS 'True if this recipe has not been built since a branch was updated.';


CREATE SEQUENCE public.sourcepackagerecipe_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackagerecipe_id_seq OWNED BY public.sourcepackagerecipe.id;


CREATE TABLE public.sourcepackagerecipebuild (
    id integer NOT NULL,
    distroseries integer NOT NULL,
    requester integer NOT NULL,
    recipe integer,
    manifest integer,
    archive integer NOT NULL,
    pocket integer NOT NULL,
    processor integer,
    virtualized boolean,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_started timestamp without time zone,
    date_finished timestamp without time zone,
    date_first_dispatched timestamp without time zone,
    builder integer,
    status integer NOT NULL,
    log integer,
    upload_log integer,
    dependencies text,
    failure_count integer DEFAULT 0 NOT NULL,
    build_farm_job integer NOT NULL
);


COMMENT ON TABLE public.sourcepackagerecipebuild IS 'The build record for the process of building a source package as described by a recipe.';


COMMENT ON COLUMN public.sourcepackagerecipebuild.distroseries IS 'The distroseries the build was for.';


COMMENT ON COLUMN public.sourcepackagerecipebuild.requester IS 'Who requested the build.';


COMMENT ON COLUMN public.sourcepackagerecipebuild.recipe IS 'The recipe being processed.';


COMMENT ON COLUMN public.sourcepackagerecipebuild.manifest IS 'The evaluated recipe that was built.';


CREATE SEQUENCE public.sourcepackagerecipebuild_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackagerecipebuild_id_seq OWNED BY public.sourcepackagerecipebuild.id;


CREATE TABLE public.sourcepackagerecipedata (
    id integer NOT NULL,
    base_branch integer,
    recipe_format text NOT NULL,
    deb_version_template text,
    revspec text,
    sourcepackage_recipe integer,
    sourcepackage_recipe_build integer,
    base_git_repository integer,
    CONSTRAINT one_base_vcs CHECK (((base_branch IS NOT NULL) <> (base_git_repository IS NOT NULL))),
    CONSTRAINT sourcepackagerecipedata__recipe_or_build_is_not_null CHECK (((sourcepackage_recipe IS NULL) <> (sourcepackage_recipe_build IS NULL)))
);


COMMENT ON TABLE public.sourcepackagerecipedata IS 'The database representation of a BaseRecipeBranch from bzr-builder.  Exactly one of sourcepackage_recipe or sourcepackage_recipe_build will be non-NULL.';


COMMENT ON COLUMN public.sourcepackagerecipedata.base_branch IS 'The branch the recipe is based on.';


COMMENT ON COLUMN public.sourcepackagerecipedata.recipe_format IS 'The format version of the recipe.';


COMMENT ON COLUMN public.sourcepackagerecipedata.deb_version_template IS 'The template for the revision number of the build.';


COMMENT ON COLUMN public.sourcepackagerecipedata.revspec IS 'The revision from base_branch to use.';


COMMENT ON COLUMN public.sourcepackagerecipedata.sourcepackage_recipe IS 'The recipe that this data is for.';


COMMENT ON COLUMN public.sourcepackagerecipedata.sourcepackage_recipe_build IS 'The build that resulted in this manifest.';


COMMENT ON COLUMN public.sourcepackagerecipedata.base_git_repository IS 'The Git repository the recipe is based on.';


CREATE SEQUENCE public.sourcepackagerecipedata_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackagerecipedata_id_seq OWNED BY public.sourcepackagerecipedata.id;


CREATE TABLE public.sourcepackagerecipedatainstruction (
    id integer NOT NULL,
    name text NOT NULL,
    type integer NOT NULL,
    comment text,
    line_number integer NOT NULL,
    branch integer,
    revspec text,
    directory text,
    recipe_data integer NOT NULL,
    parent_instruction integer,
    source_directory text,
    git_repository integer,
    CONSTRAINT one_vcs CHECK (((branch IS NOT NULL) <> (git_repository IS NOT NULL))),
    CONSTRAINT sourcepackagerecipedatainstruction__directory_not_null CHECK ((((type = 3) OR ((type = 1) AND (directory IS NULL))) OR ((type = 2) AND (directory IS NOT NULL)))),
    CONSTRAINT sourcepackagerecipedatainstruction__source_directory_null CHECK ((((type = ANY (ARRAY[1, 2])) AND (source_directory IS NULL)) OR ((type = 3) AND (source_directory IS NOT NULL))))
);


COMMENT ON TABLE public.sourcepackagerecipedatainstruction IS 'A line from the recipe, specifying a branch to nest or merge.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.name IS 'The name of the instruction.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.type IS 'The type of the instruction (MERGE == 1, NEST == 2).';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.comment IS 'The comment from the recipe about this instruction.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.line_number IS 'The line number of the instruction in the recipe.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.branch IS 'The branch being merged or nested.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.revspec IS 'The revision of the branch to use.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.directory IS 'The location to nest at, if this is a nest/nest-part instruction.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.recipe_data IS 'The SourcePackageRecipeData this instruction is part of.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.parent_instruction IS 'The nested branch this instruction applies to, or NULL for a top-level instruction.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.source_directory IS 'The location in the branch to nest, if this is a nest-part instruction.';


COMMENT ON COLUMN public.sourcepackagerecipedatainstruction.git_repository IS 'The Git repository containing the branch being merged or nested.';


CREATE SEQUENCE public.sourcepackagerecipedatainstruction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackagerecipedatainstruction_id_seq OWNED BY public.sourcepackagerecipedatainstruction.id;


CREATE TABLE public.sourcepackagerecipedistroseries (
    id integer NOT NULL,
    sourcepackagerecipe integer NOT NULL,
    distroseries integer NOT NULL
);


COMMENT ON TABLE public.sourcepackagerecipedistroseries IS 'Link table for sourcepackagerecipe and distroseries.';


COMMENT ON COLUMN public.sourcepackagerecipedistroseries.sourcepackagerecipe IS 'The primary key of the SourcePackageRecipe.';


COMMENT ON COLUMN public.sourcepackagerecipedistroseries.distroseries IS 'The primary key of the DistroSeries.';


CREATE SEQUENCE public.sourcepackagerecipedistroseries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackagerecipedistroseries_id_seq OWNED BY public.sourcepackagerecipedistroseries.id;


CREATE TABLE public.sourcepackagerelease (
    id integer NOT NULL,
    creator integer NOT NULL,
    version public.debversion NOT NULL,
    dateuploaded timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    urgency integer NOT NULL,
    dscsigningkey integer,
    component integer NOT NULL,
    changelog_entry text,
    builddepends text,
    builddependsindep text,
    architecturehintlist text NOT NULL,
    dsc text,
    section integer NOT NULL,
    maintainer integer NOT NULL,
    sourcepackagename integer NOT NULL,
    upload_distroseries integer NOT NULL,
    format integer NOT NULL,
    dsc_maintainer_rfc822 text,
    dsc_standards_version text,
    dsc_format text NOT NULL,
    dsc_binaries text,
    upload_archive integer,
    copyright text,
    build_conflicts text,
    build_conflicts_indep text,
    sourcepackage_recipe_build integer,
    changelog integer,
    user_defined_fields text,
    homepage text,
    signing_key_owner integer,
    signing_key_fingerprint text,
    buildinfo integer,
    CONSTRAINT valid_signing_key_fingerprint CHECK (((signing_key_fingerprint IS NULL) OR public.valid_fingerprint(signing_key_fingerprint))),
    CONSTRAINT valid_version CHECK (public.valid_debian_version((version)::text))
);


COMMENT ON TABLE public.sourcepackagerelease IS 'SourcePackageRelease: A source
package release. This table represents a specific release of a source
package. Source package releases may be published into a distroseries, or
even multiple distroseries.';


COMMENT ON COLUMN public.sourcepackagerelease.creator IS 'The creator of this
sourcepackagerelease. This is the person referred to in the top entry in the
package changelog in debian terms. Note that a source package maintainer in
Ubuntu might be person A, but a particular release of that source package
might in fact have been created by a different person B. The maintainer
would be recorded in the Maintainership table, while the creator of THIS
release would be recorded in the SourcePackageRelease.creator field.';


COMMENT ON COLUMN public.sourcepackagerelease.version IS 'The version string for
this source package release. E.g. "1.0-2" or "1.4-5ubuntu9.1". Note that, in
ubuntu-style and redhat-style distributions, the version+sourcepackagename
is unique, even across distroseries. In other words, you cannot have a
foo-1.2-1 package in Hoary that is different from foo-1.2-1 in Warty.';


COMMENT ON COLUMN public.sourcepackagerelease.dateuploaded IS 'The date/time that
this sourcepackagerelease was first uploaded to the Launchpad.';


COMMENT ON COLUMN public.sourcepackagerelease.urgency IS 'The urgency of the
upload. This is generally used to prioritise buildd activity but may also be
used for "testing" systems or security work in the future. The "urgency" is
set by the uploader, in the DSC file.';


COMMENT ON COLUMN public.sourcepackagerelease.dscsigningkey IS 'The GPG key used to
sign the DSC. This is not necessarily the maintainer''s key, or the
creator''s key. For example, it''s possible to produce a package, then ask a
sponsor to upload it.';


COMMENT ON COLUMN public.sourcepackagerelease.component IS 'The component in which
this sourcepackagerelease is intended (by the uploader) to reside. E.g.
main, universe, restricted. Note that the distribution managers will often
override this data and publish the package in an entirely different
component.';


COMMENT ON COLUMN public.sourcepackagerelease.changelog_entry IS 'Changelog text section extracted from the changesfile.';


COMMENT ON COLUMN public.sourcepackagerelease.builddepends IS 'The build
dependencies for this source package release.';


COMMENT ON COLUMN public.sourcepackagerelease.builddependsindep IS 'The
architecture-independant build dependancies for this source package release.';


COMMENT ON COLUMN public.sourcepackagerelease.architecturehintlist IS 'The
architectures which this source package release believes it should be built.
This is used as a hint to the build management system when deciding what
builds are still needed.';


COMMENT ON COLUMN public.sourcepackagerelease.dsc IS 'The "Debian Source Control"
file for the sourcepackagerelease, from its upload into Ubuntu for the
first time.';


COMMENT ON COLUMN public.sourcepackagerelease.section IS 'This integer field references the Section which the source package claims to be in';


COMMENT ON COLUMN public.sourcepackagerelease.maintainer IS 'Reference to the person noted as source package maintainer in the DSC.';


COMMENT ON COLUMN public.sourcepackagerelease.sourcepackagename IS 'Reference to a SourcePackageName.';


COMMENT ON COLUMN public.sourcepackagerelease.upload_distroseries IS 'The
distroseries into which this source package release was uploaded into
Launchpad / Ubuntu for the first time. In general, this will be the
development Ubuntu release into which this package was uploaded. For a
package which was unchanged between warty and hoary, this would show Warty.
For a package which was uploaded into Hoary, this would show Hoary.';


COMMENT ON COLUMN public.sourcepackagerelease.format IS 'The format of this
sourcepackage release, e.g. DPKG, RPM, EBUILD, etc. This is an enum, and the
values are listed in dbschema.SourcePackageFormat';


COMMENT ON COLUMN public.sourcepackagerelease.dsc_maintainer_rfc822 IS 'The original maintainer line in RFC-822 format, to be used in archive indexes.';


COMMENT ON COLUMN public.sourcepackagerelease.dsc_standards_version IS 'DSC standards version (such as "3.6.2", "3.5.9", etc) used to build this source.';


COMMENT ON COLUMN public.sourcepackagerelease.dsc_format IS 'DSC format version (such as "1.0").';


COMMENT ON COLUMN public.sourcepackagerelease.dsc_binaries IS 'DSC binary line, claimed binary-names produce by this source.';


COMMENT ON COLUMN public.sourcepackagerelease.upload_archive IS 'The archive into which this sourcepackagerelese was originally uploaded.';


COMMENT ON COLUMN public.sourcepackagerelease.copyright IS 'The copyright associated with this sourcepackage. Often in the case of debian packages and will be found after the installation in /usr/share/doc/<binarypackagename>/copyright';


COMMENT ON COLUMN public.sourcepackagerelease.build_conflicts IS 'The list of packages that will conflict with this source while building, as mentioned in the control file "Build-Conflicts:" field.';


COMMENT ON COLUMN public.sourcepackagerelease.build_conflicts_indep IS 'The list of packages that will conflict with this source while building in architecture independent environment, as mentioned in the control file "Build-Conflicts-Indep:" field.';


COMMENT ON COLUMN public.sourcepackagerelease.changelog IS 'The LibraryFileAlias ID of changelog associated with this sourcepackage.  Often in the case of debian packages and will be found after the installation in /usr/share/doc/<binarypackagename>/changelog.Debian.gz';


COMMENT ON COLUMN public.sourcepackagerelease.user_defined_fields IS 'A JSON struct containing a sequence of key-value pairs with user defined fields in the control file.';


COMMENT ON COLUMN public.sourcepackagerelease.homepage IS 'Upstream project homepage URL, not checked for validity.';


CREATE SEQUENCE public.sourcepackagerelease_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackagerelease_id_seq OWNED BY public.sourcepackagerelease.id;


CREATE TABLE public.sourcepackagereleasefile (
    sourcepackagerelease integer NOT NULL,
    libraryfile integer NOT NULL,
    filetype integer NOT NULL,
    id integer DEFAULT nextval(('sourcepackagereleasefile_id_seq'::text)::regclass) NOT NULL
);


COMMENT ON TABLE public.sourcepackagereleasefile IS 'SourcePackageReleaseFile: A soyuz source package release file. This table links sourcepackagereleasehistory records to the files which comprise the input.';


COMMENT ON COLUMN public.sourcepackagereleasefile.sourcepackagerelease IS 'The sourcepackagerelease that this file belongs to';


COMMENT ON COLUMN public.sourcepackagereleasefile.libraryfile IS 'The libraryfilealias embodying this file';


COMMENT ON COLUMN public.sourcepackagereleasefile.filetype IS 'The type of the file. E.g. TAR, DIFF, DSC';


CREATE SEQUENCE public.sourcepackagereleasefile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sourcepackagereleasefile_id_seq OWNED BY public.sourcepackagereleasefile.id;


CREATE TABLE public.specification (
    id integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text,
    owner integer NOT NULL,
    assignee integer,
    drafter integer,
    approver integer,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    product integer,
    productseries integer,
    distribution integer,
    distroseries integer,
    milestone integer,
    definition_status integer NOT NULL,
    priority integer DEFAULT 5 NOT NULL,
    specurl text,
    whiteboard text,
    superseded_by integer,
    direction_approved boolean DEFAULT false NOT NULL,
    man_days integer,
    implementation_status integer DEFAULT 0 NOT NULL,
    goalstatus integer DEFAULT 30 NOT NULL,
    fti public.ts2_tsvector,
    goal_proposer integer,
    date_goal_proposed timestamp without time zone,
    goal_decider integer,
    date_goal_decided timestamp without time zone,
    completer integer,
    date_completed timestamp without time zone,
    starter integer,
    date_started timestamp without time zone,
    private boolean DEFAULT false NOT NULL,
    date_last_changed timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    last_changed_by integer,
    information_type integer DEFAULT 1 NOT NULL,
    access_policy integer,
    access_grants integer[],
    CONSTRAINT distribution_and_distroseries CHECK (((distroseries IS NULL) OR (distribution IS NOT NULL))),
    CONSTRAINT product_and_productseries CHECK (((productseries IS NULL) OR (product IS NOT NULL))),
    CONSTRAINT product_xor_distribution CHECK (((product IS NULL) <> (distribution IS NULL))),
    CONSTRAINT specification_completion_fully_recorded_chk CHECK (((date_completed IS NULL) = (completer IS NULL))),
    CONSTRAINT specification_completion_recorded_chk CHECK (((date_completed IS NULL) <> (((implementation_status = 90) OR (definition_status = ANY (ARRAY[60, 70]))) OR ((implementation_status = 95) AND (definition_status = 10))))),
    CONSTRAINT specification_decision_recorded CHECK (((goalstatus = 30) OR ((goal_decider IS NOT NULL) AND (date_goal_decided IS NOT NULL)))),
    CONSTRAINT specification_goal_nomination_chk CHECK ((((productseries IS NULL) AND (distroseries IS NULL)) OR ((goal_proposer IS NOT NULL) AND (date_goal_proposed IS NOT NULL)))),
    CONSTRAINT specification_not_self_superseding CHECK ((superseded_by <> id)),
    CONSTRAINT specification_start_fully_recorded_chk CHECK (((date_started IS NULL) = (starter IS NULL))),
    CONSTRAINT specification_start_recorded_chk CHECK (((date_started IS NULL) <> ((implementation_status <> ALL (ARRAY[0, 5, 10, 95])) OR ((implementation_status = 95) AND (definition_status = 10))))),
    CONSTRAINT valid_name CHECK (public.valid_name(name)),
    CONSTRAINT valid_url CHECK (public.valid_absolute_url(specurl))
);


COMMENT ON TABLE public.specification IS 'A feature specification. At the moment we do not store the actual specification, we store a URL for the spec, which is managed in a wiki somewhere else. We store the overall state of the spec, as well as queueing information about who needs to review the spec, and why.';


COMMENT ON COLUMN public.specification.assignee IS 'The person who has been assigned to implement this specification.';


COMMENT ON COLUMN public.specification.drafter IS 'The person who has been asked to draft this specification. They are responsible for getting the spec to "approved" state.';


COMMENT ON COLUMN public.specification.approver IS 'The person who is responsible for approving the specification in due course, and who will probably be required to review the code itself when it is being implemented.';


COMMENT ON COLUMN public.specification.product IS 'The product for which this is a feature specification. The specification must be connected either to a product, or to a distribution.';


COMMENT ON COLUMN public.specification.productseries IS 'This is an indicator that the specification is planned, or targeted, for implementation in a given product series. It is not necessary to target a spec to a series, but it is a useful way of showing which specs are planned to implement for a given series.';


COMMENT ON COLUMN public.specification.distribution IS 'The distribution for which this is a feature specification. The specification must be connected either to a product, or to a distribution.';


COMMENT ON COLUMN public.specification.distroseries IS 'If this is not NULL, then it means that the release managers have targeted this feature to be released in the given distroseries. It is not necessary to target a distroseries, but this is a useful way of know which specifications are, for example, BreezyGoals.';


COMMENT ON COLUMN public.specification.milestone IS 'This is an indicator that the feature defined in this specification is expected to be delivered for a given milestone. Note that milestones are not necessarily releases, they are a way of identifying a point in time and grouping bugs and features around that.';


COMMENT ON COLUMN public.specification.definition_status IS 'An enum called SpecificationDefinitionStatus that shows what the current status (new, draft, implemented etc) the spec is currently in.';


COMMENT ON COLUMN public.specification.priority IS 'An enum that gives the implementation priority (low, medium, high, emergency) of the feature defined in this specification.';


COMMENT ON COLUMN public.specification.specurl IS 'The URL where the specification itself can be found. This is usually a wiki page somewhere.';


COMMENT ON COLUMN public.specification.whiteboard IS 'As long as the specification is somewhere else (i.e. not in Launchpad) it will be useful to have a place to hold some arbitrary message or status flags that have meaning to the project, not Launchpad. This whiteboard is just the place for it.';


COMMENT ON COLUMN public.specification.superseded_by IS 'The specification which replaced this specification.';


COMMENT ON COLUMN public.specification.implementation_status IS 'The implementation status of this specification. This field is used to track the actual delivery of the feature (implementing the spec), as opposed to the definition of expected behaviour (writing the spec).';


COMMENT ON COLUMN public.specification.goalstatus IS 'Whether or not the drivers for the goal product series or distro release have accepted this specification as a goal.';


COMMENT ON COLUMN public.specification.goal_proposer IS 'The person who proposed this spec as a goal for the productseries or distroseries.';


COMMENT ON COLUMN public.specification.date_goal_proposed IS 'The date the spec was proposed as a goal.';


COMMENT ON COLUMN public.specification.goal_decider IS 'The person who approved or declined this goal.';


COMMENT ON COLUMN public.specification.date_goal_decided IS 'The date this goal was accepted or declined.';


COMMENT ON COLUMN public.specification.completer IS 'The person who changed the state of the spec in such a way that it was determined to be completed.';


COMMENT ON COLUMN public.specification.date_completed IS 'The date this specification was completed or marked obsolete. This lets us chart the progress of a project (or a release) over time in terms of features implemented.';


COMMENT ON COLUMN public.specification.private IS 'Specification is private.';


COMMENT ON COLUMN public.specification.information_type IS 'Enum describing what type of information is stored, such as type of private or security related data, and used to determine how to apply an access policy.';


COMMENT ON CONSTRAINT specification_completion_fully_recorded_chk ON public.specification IS 'A constraint that ensures, where we have a date_completed, that we also have a completer. This means that the resolution was fully recorded.';


CREATE SEQUENCE public.specification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.specification_id_seq OWNED BY public.specification.id;


CREATE TABLE public.specificationbranch (
    id integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    specification integer NOT NULL,
    branch integer NOT NULL,
    summary text,
    registrant integer NOT NULL
);


COMMENT ON TABLE public.specificationbranch IS 'A branch related to a specification, most likely a branch for implementing the specification.  It is possible to have multiple branches for a given specification especially in the situation where the specification requires modifying multiple products.';


COMMENT ON COLUMN public.specificationbranch.specification IS 'The specification associated with this branch.';


COMMENT ON COLUMN public.specificationbranch.branch IS 'The branch associated to the specification.';


COMMENT ON COLUMN public.specificationbranch.registrant IS 'The person who linked the specification to the branch.';


CREATE SEQUENCE public.specificationbranch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.specificationbranch_id_seq OWNED BY public.specificationbranch.id;


CREATE TABLE public.specificationdependency (
    id integer NOT NULL,
    specification integer NOT NULL,
    dependency integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT specificationdependency_not_self CHECK ((specification <> dependency))
);


COMMENT ON TABLE public.specificationdependency IS 'A table that stores information about which specification needs to be implemented before another specification can be implemented. We can create a chain of dependencies, and use that information for scheduling and prioritisation of work.';


COMMENT ON COLUMN public.specificationdependency.specification IS 'The spec for which we are creating a dependency.';


COMMENT ON COLUMN public.specificationdependency.dependency IS 'The spec on which it is dependant.';


CREATE SEQUENCE public.specificationdependency_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.specificationdependency_id_seq OWNED BY public.specificationdependency.id;


CREATE TABLE public.specificationmessage (
    id integer NOT NULL,
    specification integer,
    message integer,
    visible boolean DEFAULT true NOT NULL
);


COMMENT ON TABLE public.specificationmessage IS 'Comments and discussion on a Specification.';


CREATE SEQUENCE public.specificationmessage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.specificationmessage_id_seq OWNED BY public.specificationmessage.id;


CREATE TABLE public.specificationsubscription (
    id integer NOT NULL,
    specification integer NOT NULL,
    person integer NOT NULL,
    essential boolean DEFAULT false NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.specificationsubscription IS 'A table capturing a subscription of a person to a specification.';


COMMENT ON COLUMN public.specificationsubscription.essential IS 'A field that indicates whether or not this person is essential to discussions on the planned feature. This is used by the meeting scheduler to ensure that all the essential people are at any automatically scheduled BOFs discussing that spec.';


CREATE SEQUENCE public.specificationsubscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.specificationsubscription_id_seq OWNED BY public.specificationsubscription.id;


CREATE TABLE public.specificationworkitem (
    id integer NOT NULL,
    title text NOT NULL,
    specification integer NOT NULL,
    assignee integer,
    milestone integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    status integer NOT NULL,
    sequence integer NOT NULL,
    deleted boolean DEFAULT false NOT NULL
);


COMMENT ON TABLE public.specificationworkitem IS 'A work item which is a piece of work relating to a blueprint.';


COMMENT ON COLUMN public.specificationworkitem.id IS 'The id of the work item.';


COMMENT ON COLUMN public.specificationworkitem.title IS 'The title of the work item.';


COMMENT ON COLUMN public.specificationworkitem.specification IS 'The blueprint that this work item is a part of.';


COMMENT ON COLUMN public.specificationworkitem.assignee IS 'The person who is assigned to complete the work item.';


COMMENT ON COLUMN public.specificationworkitem.milestone IS 'The milestone this work item is targetted to.';


COMMENT ON COLUMN public.specificationworkitem.date_created IS 'The date on which the work item was created.';


COMMENT ON COLUMN public.specificationworkitem.sequence IS 'The sequence number specifies the order of work items in the UI.';


COMMENT ON COLUMN public.specificationworkitem.deleted IS 'Marks if the work item has been deleted. To be able to keep history we do not want to actually delete them from the database.';


CREATE SEQUENCE public.specificationworkitem_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.specificationworkitem_id_seq OWNED BY public.specificationworkitem.id;


CREATE TABLE public.spokenin (
    language integer NOT NULL,
    country integer NOT NULL,
    id integer DEFAULT nextval(('spokenin_id_seq'::text)::regclass) NOT NULL
);


CREATE SEQUENCE public.spokenin_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.spokenin_id_seq OWNED BY public.spokenin.id;


CREATE TABLE public.sprint (
    id integer NOT NULL,
    owner integer NOT NULL,
    name text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
    home_page text,
    address text,
    time_zone text NOT NULL,
    time_starts timestamp without time zone NOT NULL,
    time_ends timestamp without time zone NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    driver integer,
    homepage_content text,
    icon integer,
    mugshot integer,
    logo integer,
    is_physical boolean DEFAULT true NOT NULL,
    CONSTRAINT sprint_starts_before_ends CHECK ((time_starts < time_ends))
);


COMMENT ON TABLE public.sprint IS 'A meeting, sprint or conference. This is a convenient way to keep track of a collection of specs that will be discussed, and the people that will be attending.';


COMMENT ON COLUMN public.sprint.time_zone IS 'The timezone of the sprint, stored in text format from the Olsen database names, like "US/Eastern".';


COMMENT ON COLUMN public.sprint.driver IS 'The driver (together with the registrant or owner) is responsible for deciding which topics will be accepted onto the agenda of the sprint.';


COMMENT ON COLUMN public.sprint.homepage_content IS 'A home page for this sprint in the Launchpad.';


COMMENT ON COLUMN public.sprint.icon IS 'The library file alias to a small image to be used as an icon whenever we are referring to a sprint.';


COMMENT ON COLUMN public.sprint.mugshot IS 'The library file alias of a mugshot image to display as the branding of a sprint, on its home page.';


COMMENT ON COLUMN public.sprint.logo IS 'The library file alias of a smaller version of this sprint''s mugshot.';


COMMENT ON COLUMN public.sprint.is_physical IS 'Is the sprint being held in a physical location?';


CREATE SEQUENCE public.sprint_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sprint_id_seq OWNED BY public.sprint.id;


CREATE TABLE public.sprintattendance (
    id integer NOT NULL,
    attendee integer NOT NULL,
    sprint integer NOT NULL,
    time_starts timestamp without time zone NOT NULL,
    time_ends timestamp without time zone NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    is_physical boolean DEFAULT false NOT NULL,
    CONSTRAINT sprintattendance_starts_before_ends CHECK ((time_starts < time_ends))
);


COMMENT ON TABLE public.sprintattendance IS 'The record that someone will be attending a particular sprint or meeting.';


COMMENT ON COLUMN public.sprintattendance.attendee IS 'The person attending the sprint.';


COMMENT ON COLUMN public.sprintattendance.sprint IS 'The sprint the person is attending.';


COMMENT ON COLUMN public.sprintattendance.time_starts IS 'The time from which the person will be available to participate in meetings at the sprint.';


COMMENT ON COLUMN public.sprintattendance.time_ends IS 'The time of departure from the sprint or conference - this is the last time at which the person is available for meetings during the sprint.';


COMMENT ON COLUMN public.sprintattendance.is_physical IS 'Is the person physically attending the sprint';


CREATE SEQUENCE public.sprintattendance_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sprintattendance_id_seq OWNED BY public.sprintattendance.id;


CREATE TABLE public.sprintspecification (
    id integer NOT NULL,
    sprint integer NOT NULL,
    specification integer NOT NULL,
    status integer DEFAULT 30 NOT NULL,
    whiteboard text,
    registrant integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    decider integer,
    date_decided timestamp without time zone,
    CONSTRAINT sprintspecification_decision_recorded CHECK (((status = 30) OR ((decider IS NOT NULL) AND (date_decided IS NOT NULL))))
);


COMMENT ON TABLE public.sprintspecification IS 'The link between a sprint and a specification, so that we know which specs are going to be discussed at which sprint.';


COMMENT ON COLUMN public.sprintspecification.status IS 'Whether or not the spec has been approved on the agenda for this sprint.';


COMMENT ON COLUMN public.sprintspecification.whiteboard IS 'A place to store comments specifically related to this spec being on the agenda of this meeting.';


COMMENT ON COLUMN public.sprintspecification.registrant IS 'The person who nominated this specification for the agenda of the sprint.';


COMMENT ON COLUMN public.sprintspecification.decider IS 'The person who approved or declined this specification for the sprint agenda.';


COMMENT ON COLUMN public.sprintspecification.date_decided IS 'The date this specification was approved or declined for the agenda.';


CREATE SEQUENCE public.sprintspecification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sprintspecification_id_seq OWNED BY public.sprintspecification.id;


CREATE TABLE public.sshkey (
    id integer NOT NULL,
    person integer,
    keytype integer NOT NULL,
    keytext text NOT NULL,
    comment text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


CREATE SEQUENCE public.sshkey_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sshkey_id_seq OWNED BY public.sshkey.id;


CREATE TABLE public.structuralsubscription (
    id integer NOT NULL,
    product integer,
    productseries integer,
    project integer,
    milestone integer,
    distribution integer,
    distroseries integer,
    sourcepackagename integer,
    subscriber integer NOT NULL,
    subscribed_by integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_updated timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    CONSTRAINT one_target CHECK ((public.null_count(ARRAY[product, productseries, project, distroseries, distribution, milestone]) = 5)),
    CONSTRAINT sourcepackagename_requires_distribution CHECK (((sourcepackagename IS NULL) OR (distribution IS NOT NULL)))
);


COMMENT ON TABLE public.structuralsubscription IS 'A subscription to notifications about a Launchpad structure';


COMMENT ON COLUMN public.structuralsubscription.product IS 'The subscription`s target, when it is a product.';


COMMENT ON COLUMN public.structuralsubscription.productseries IS 'The subscription`s target, when it is a product series.';


COMMENT ON COLUMN public.structuralsubscription.project IS 'The subscription`s target, when it is a project.';


COMMENT ON COLUMN public.structuralsubscription.milestone IS 'The subscription`s target, when it is a milestone.';


COMMENT ON COLUMN public.structuralsubscription.distribution IS 'The subscription`s target, when it is a distribution.';


COMMENT ON COLUMN public.structuralsubscription.distroseries IS 'The subscription`s target, when it is a distribution series.';


COMMENT ON COLUMN public.structuralsubscription.sourcepackagename IS 'The subscription`s target, when it is a source-package';


COMMENT ON COLUMN public.structuralsubscription.subscriber IS 'The person subscribed.';


COMMENT ON COLUMN public.structuralsubscription.subscribed_by IS 'The person initiating the subscription.';


COMMENT ON COLUMN public.structuralsubscription.date_created IS 'The date on which this subscription was created.';


COMMENT ON COLUMN public.structuralsubscription.date_last_updated IS 'The date on which this subscription was last updated.';


CREATE SEQUENCE public.structuralsubscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.structuralsubscription_id_seq OWNED BY public.structuralsubscription.id;


CREATE TABLE public.suggestivepotemplate (
    potemplate integer NOT NULL
);


COMMENT ON TABLE public.suggestivepotemplate IS 'Cache of POTemplates that can provide external translation suggestions.';


CREATE TABLE public.teammembership (
    id integer NOT NULL,
    person integer NOT NULL,
    team integer NOT NULL,
    status integer NOT NULL,
    date_joined timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    date_expires timestamp without time zone,
    last_changed_by integer,
    last_change_comment text,
    proposed_by integer,
    acknowledged_by integer,
    reviewed_by integer,
    date_proposed timestamp without time zone,
    date_last_changed timestamp without time zone,
    date_acknowledged timestamp without time zone,
    date_reviewed timestamp without time zone,
    proponent_comment text,
    acknowledger_comment text,
    reviewer_comment text,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.teammembership IS 'The direct membership of a person on a given team.';


COMMENT ON COLUMN public.teammembership.person IS 'The person.';


COMMENT ON COLUMN public.teammembership.team IS 'The team.';


COMMENT ON COLUMN public.teammembership.status IS 'The state of the membership.';


COMMENT ON COLUMN public.teammembership.date_joined IS 'The date this membership was made active for the first time.';


COMMENT ON COLUMN public.teammembership.date_expires IS 'The date this membership will expire, if any.';


COMMENT ON COLUMN public.teammembership.last_changed_by IS 'The person who reviewed the last change to this membership.';


COMMENT ON COLUMN public.teammembership.last_change_comment IS 'The comment left by the reviewer for the change.';


COMMENT ON COLUMN public.teammembership.proposed_by IS 'The user who proposed the person as member of the team.';


COMMENT ON COLUMN public.teammembership.acknowledged_by IS 'The member (or someone acting on their behalf) who accepts an invitation to join a team';


COMMENT ON COLUMN public.teammembership.reviewed_by IS 'The team admin who reviewed (approved/declined) the membership.';


COMMENT ON COLUMN public.teammembership.date_proposed IS 'The date of the proposal.';


COMMENT ON COLUMN public.teammembership.date_last_changed IS 'The date this membership was last changed.';


COMMENT ON COLUMN public.teammembership.date_acknowledged IS 'The date of acknowledgement.';


COMMENT ON COLUMN public.teammembership.date_reviewed IS 'The date the membership was
approved/declined.';


COMMENT ON COLUMN public.teammembership.proponent_comment IS 'The comment left by the proponent.';


COMMENT ON COLUMN public.teammembership.acknowledger_comment IS 'The comment left by the person who acknowledged the membership.';


COMMENT ON COLUMN public.teammembership.reviewer_comment IS 'The comment left by the approver.';


COMMENT ON COLUMN public.teammembership.date_created IS 'The date this membership was created.';


CREATE SEQUENCE public.teammembership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.teammembership_id_seq OWNED BY public.teammembership.id;


CREATE TABLE public.teamparticipation (
    id integer NOT NULL,
    team integer NOT NULL,
    person integer NOT NULL
);


COMMENT ON TABLE public.teamparticipation IS 'The participation of a person on a team, which can be a direct or indirect membership.';


COMMENT ON COLUMN public.teamparticipation.team IS 'The team.';


COMMENT ON COLUMN public.teamparticipation.person IS 'The member.';


CREATE SEQUENCE public.teamparticipation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.teamparticipation_id_seq OWNED BY public.teamparticipation.id;


CREATE TABLE public.temporaryblobstorage (
    id integer NOT NULL,
    uuid text NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    file_alias integer NOT NULL
);


CREATE SEQUENCE public.temporaryblobstorage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.temporaryblobstorage_id_seq OWNED BY public.temporaryblobstorage.id;


CREATE TABLE public.translationgroup (
    id integer NOT NULL,
    name text NOT NULL,
    title text,
    summary text,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    owner integer NOT NULL,
    translation_guide_url text
);


COMMENT ON TABLE public.translationgroup IS 'This represents an organised translation group that spans multiple languages. Effectively it consists of a list of people (pointers to Person), and each Person is associated with a Language. So, for each TranslationGroup we can ask the question "in this TranslationGroup, who is responsible for translating into Arabic?", for example.';


COMMENT ON COLUMN public.translationgroup.translation_guide_url IS 'URL with documentation about general rules for translation work done by this translation group.';


CREATE SEQUENCE public.translationgroup_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.translationgroup_id_seq OWNED BY public.translationgroup.id;


CREATE TABLE public.translationimportqueueentry (
    id integer NOT NULL,
    path text NOT NULL,
    content integer NOT NULL,
    importer integer NOT NULL,
    dateimported timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    distroseries integer,
    sourcepackagename integer,
    productseries integer,
    by_maintainer boolean NOT NULL,
    pofile integer,
    potemplate integer,
    status integer DEFAULT 5 NOT NULL,
    date_status_changed timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    format integer DEFAULT 1 NOT NULL,
    error_output text,
    CONSTRAINT valid_link CHECK ((((productseries IS NULL) <> (distroseries IS NULL)) AND ((distroseries IS NULL) = (sourcepackagename IS NULL))))
);


COMMENT ON TABLE public.translationimportqueueentry IS 'Queue with translatable resources pending to be imported into Rosetta.';


COMMENT ON COLUMN public.translationimportqueueentry.path IS 'The path (included the filename) where this file was stored when we imported it.';


COMMENT ON COLUMN public.translationimportqueueentry.content IS 'The file content that is being imported.';


COMMENT ON COLUMN public.translationimportqueueentry.importer IS 'The person that did the import.';


COMMENT ON COLUMN public.translationimportqueueentry.dateimported IS 'The timestamp when the import was done.';


COMMENT ON COLUMN public.translationimportqueueentry.distroseries IS 'The distribution release related to this import.';


COMMENT ON COLUMN public.translationimportqueueentry.sourcepackagename IS 'The source package name related to this import.';


COMMENT ON COLUMN public.translationimportqueueentry.productseries IS 'The product series related to this import.';


COMMENT ON COLUMN public.translationimportqueueentry.by_maintainer IS 'Notes whether this upload was done by the maintiner of the package or project.';


COMMENT ON COLUMN public.translationimportqueueentry.pofile IS 'Link to the POFile where this import will end.';


COMMENT ON COLUMN public.translationimportqueueentry.potemplate IS 'Link to the POTemplate where this import will end.';


COMMENT ON COLUMN public.translationimportqueueentry.status IS 'The status of the import: 1 Approved, 2 Imported, 3 Deleted, 4 Failed, 5 Needs Review, 6 Blocked.';


COMMENT ON COLUMN public.translationimportqueueentry.date_status_changed IS 'The date when the status of this entry was changed.';


COMMENT ON COLUMN public.translationimportqueueentry.format IS 'The file format of the content that is being imported.';


COMMENT ON COLUMN public.translationimportqueueentry.error_output IS 'Error output from last import attempt.';


CREATE SEQUENCE public.translationimportqueueentry_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.translationimportqueueentry_id_seq OWNED BY public.translationimportqueueentry.id;


CREATE TABLE public.translationmessage (
    id integer NOT NULL,
    potmsgset integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    submitter integer NOT NULL,
    date_reviewed timestamp without time zone,
    reviewer integer,
    msgstr0 integer,
    msgstr1 integer,
    msgstr2 integer,
    msgstr3 integer,
    comment text,
    origin integer NOT NULL,
    validation_status integer DEFAULT 0 NOT NULL,
    is_current_ubuntu boolean DEFAULT false NOT NULL,
    is_fuzzy boolean DEFAULT false NOT NULL,
    is_current_upstream boolean DEFAULT false NOT NULL,
    was_obsolete_in_last_import boolean DEFAULT false NOT NULL,
    was_fuzzy_in_last_import boolean DEFAULT false NOT NULL,
    msgstr4 integer,
    msgstr5 integer,
    potemplate integer,
    language integer,
    msgid_singular integer,
    msgid_plural integer,
    suggestive boolean,
    CONSTRAINT translationmessage__reviewer__date_reviewed__valid CHECK (((reviewer IS NULL) = (date_reviewed IS NULL)))
);


COMMENT ON TABLE public.translationmessage IS 'This table stores a concrete
translation for a POTMsgSet message. It knows who, when and where did it,
and whether it was reviewed by someone and when was it reviewed.';


COMMENT ON COLUMN public.translationmessage.potmsgset IS 'The template message which
this translation message is a translation of.';


COMMENT ON COLUMN public.translationmessage.date_created IS 'The date we saw this
translation first.';


COMMENT ON COLUMN public.translationmessage.submitter IS 'The person that made
the submission through the web to Launchpad, or the last translator on the
translation file that we are processing, or the person who uploaded that
pofile to Launchpad. In short, our best guess as to the person who is
contributing that translation.';


COMMENT ON COLUMN public.translationmessage.date_reviewed IS 'The date when this
message was reviewed for last time.';


COMMENT ON COLUMN public.translationmessage.reviewer IS 'The person who did the
review and accepted current translations.';


COMMENT ON COLUMN public.translationmessage.msgstr0 IS 'Translation for plural form 0
(if any).';


COMMENT ON COLUMN public.translationmessage.msgstr1 IS 'Translation for plural form 1
(if any).';


COMMENT ON COLUMN public.translationmessage.msgstr2 IS 'Translation for plural form 2
(if any).';


COMMENT ON COLUMN public.translationmessage.msgstr3 IS 'Translation for plural form 3
(if any).';


COMMENT ON COLUMN public.translationmessage.comment IS 'Text of translator
comment from the translation file.';


COMMENT ON COLUMN public.translationmessage.origin IS 'The source of this
translation. This indicates whether the translation was in a translation file
that we parsed (probably one published in a package or branch or tarball), in
which case its value will be 1, or was submitted through the web, in which
case its value will be 2.';


COMMENT ON COLUMN public.translationmessage.validation_status IS 'Whether we have
validated this translation. Being 0 the value that says this row has not been
validated yet, 1 the value that says it is correct and 2 the value noting that
there was an unknown error with the validation.';


COMMENT ON COLUMN public.translationmessage.is_current_ubuntu IS 'Whether this translation
is being used in Ubuntu.';


COMMENT ON COLUMN public.translationmessage.is_fuzzy IS 'Whether this translation
must be checked before use it.';


COMMENT ON COLUMN public.translationmessage.is_current_upstream IS 'Whether this translation
is being used upstream.';


COMMENT ON COLUMN public.translationmessage.was_obsolete_in_last_import IS 'Whether
this translation was obsolete in last imported file.';


COMMENT ON COLUMN public.translationmessage.was_fuzzy_in_last_import IS 'Whether this
imported translation must be checked before use it.';


CREATE SEQUENCE public.translationmessage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.translationmessage_id_seq OWNED BY public.translationmessage.id;


CREATE TABLE public.translationrelicensingagreement (
    id integer NOT NULL,
    person integer NOT NULL,
    allow_relicensing boolean DEFAULT true NOT NULL,
    date_decided timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);


COMMENT ON TABLE public.translationrelicensingagreement IS 'Who of translation contributors wants their translations relicensed and who does not.';


COMMENT ON COLUMN public.translationrelicensingagreement.person IS 'A translator which has submitted their answer.';


COMMENT ON COLUMN public.translationrelicensingagreement.allow_relicensing IS 'Does this person want their translations relicensed under BSD.';


COMMENT ON COLUMN public.translationrelicensingagreement.date_decided IS 'Date when the last change of opinion was registered.';


CREATE SEQUENCE public.translationrelicensingagreement_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.translationrelicensingagreement_id_seq OWNED BY public.translationrelicensingagreement.id;


CREATE TABLE public.translationtemplateitem (
    id integer NOT NULL,
    potemplate integer NOT NULL,
    sequence integer NOT NULL,
    potmsgset integer NOT NULL,
    msgid_singular integer,
    msgid_plural integer,
    CONSTRAINT translationtemplateitem_sequence_check CHECK ((sequence >= 0))
);


CREATE SEQUENCE public.translationtemplateitem_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.translationtemplateitem_id_seq OWNED BY public.translationtemplateitem.id;


CREATE TABLE public.translationtemplatesbuild (
    id integer NOT NULL,
    build_farm_job integer NOT NULL,
    branch integer NOT NULL,
    processor integer,
    virtualized boolean,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    date_started timestamp without time zone,
    date_finished timestamp without time zone,
    date_first_dispatched timestamp without time zone,
    builder integer,
    status integer,
    log integer,
    failure_count integer DEFAULT 0
);


COMMENT ON TABLE public.translationtemplatesbuild IS 'Build-farm record of a translation templates build.';


COMMENT ON COLUMN public.translationtemplatesbuild.build_farm_job IS 'Associated BuildFarmJob.';


COMMENT ON COLUMN public.translationtemplatesbuild.branch IS 'Branch to build templates out of.';


CREATE SEQUENCE public.translationtemplatesbuild_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.translationtemplatesbuild_id_seq OWNED BY public.translationtemplatesbuild.id;


CREATE TABLE public.translator (
    id integer NOT NULL,
    translationgroup integer NOT NULL,
    language integer NOT NULL,
    translator integer NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    style_guide_url text
);


COMMENT ON TABLE public.translator IS 'A translator is a person in a TranslationGroup who is responsible for a particular language. At the moment, there can only be one person in a TranslationGroup who is the Translator for a particular language. If you want multiple people, then create a launchpad team and assign that team to the language.';


COMMENT ON COLUMN public.translator.translationgroup IS 'The TranslationGroup for which this Translator is working.';


COMMENT ON COLUMN public.translator.language IS 'The language for which this Translator is responsible in this TranslationGroup. Note that the same person may be responsible for multiple languages, but any given language can only have one Translator within the TranslationGroup.';


COMMENT ON COLUMN public.translator.translator IS 'The Person who is responsible for this language in this translation group.';


COMMENT ON COLUMN public.translator.style_guide_url IS 'URL with translation style guide of a particular translation team.';


CREATE SEQUENCE public.translator_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.translator_id_seq OWNED BY public.translator.id;


CREATE TABLE public.usertouseremail (
    id integer NOT NULL,
    sender integer NOT NULL,
    recipient integer NOT NULL,
    date_sent timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    subject text NOT NULL,
    message_id text NOT NULL
);


COMMENT ON TABLE public.usertouseremail IS 'A log of all direct user-to-user email contacts that have gone through Launchpad.';


COMMENT ON COLUMN public.usertouseremail.sender IS 'The person sending this email.';


COMMENT ON COLUMN public.usertouseremail.recipient IS 'The person receiving this email.';


COMMENT ON COLUMN public.usertouseremail.date_sent IS 'The date the email was sent.';


COMMENT ON COLUMN public.usertouseremail.subject IS 'The Subject: header.';


COMMENT ON COLUMN public.usertouseremail.message_id IS 'The Message-ID: header.';


CREATE SEQUENCE public.usertouseremail_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usertouseremail_id_seq OWNED BY public.usertouseremail.id;


CREATE VIEW public.validpersoncache AS
 SELECT emailaddress.person AS id
   FROM public.emailaddress,
    public.person,
    public.account
  WHERE ((((emailaddress.person = person.id) AND (person.account = account.id)) AND (emailaddress.status = 4)) AND (account.status = 20));


COMMENT ON VIEW public.validpersoncache IS 'A materialized view listing the Person.ids of all valid people (but not teams).';


CREATE VIEW public.validpersonorteamcache AS
 SELECT person.id
   FROM ((public.person
     LEFT JOIN public.emailaddress ON ((person.id = emailaddress.person)))
     LEFT JOIN public.account ON ((person.account = account.id)))
  WHERE (((person.teamowner IS NOT NULL) AND (person.merged IS NULL)) OR (((person.teamowner IS NULL) AND (account.status = 20)) AND (emailaddress.status = 4)));


CREATE TABLE public.vote (
    id integer NOT NULL,
    person integer,
    poll integer NOT NULL,
    preference integer,
    option integer,
    token text NOT NULL
);


COMMENT ON TABLE public.vote IS 'The table where we store the actual votes of people.  It may or may not have a reference to the person who voted, depending on the poll''s secrecy.';


COMMENT ON COLUMN public.vote.person IS 'The person who voted. It''s NULL for secret polls.';


COMMENT ON COLUMN public.vote.poll IS 'The poll for which this vote applies.';


COMMENT ON COLUMN public.vote.preference IS 'Used to identify in what order the options were chosen by a given user (in case of preferential voting).';


COMMENT ON COLUMN public.vote.option IS 'The choosen option.';


COMMENT ON COLUMN public.vote.token IS 'A unique token that''s given to the user so they can change their vote later.';


CREATE SEQUENCE public.vote_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vote_id_seq OWNED BY public.vote.id;


CREATE TABLE public.votecast (
    id integer NOT NULL,
    person integer NOT NULL,
    poll integer NOT NULL
);


COMMENT ON TABLE public.votecast IS 'Here we store who has already voted in a poll, to ensure they do not vote again, and potentially to notify people that they may still vote.';


COMMENT ON COLUMN public.votecast.person IS 'The person who voted.';


COMMENT ON COLUMN public.votecast.poll IS 'The poll in which this person voted.';


CREATE SEQUENCE public.votecast_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.votecast_id_seq OWNED BY public.votecast.id;


CREATE TABLE public.webhook (
    id integer NOT NULL,
    registrant integer NOT NULL,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    delivery_url text NOT NULL,
    secret text,
    json_data text NOT NULL,
    git_repository integer,
    branch integer,
    snap integer,
    CONSTRAINT one_target CHECK ((public.null_count(ARRAY[git_repository, branch, snap]) = 2))
);


CREATE SEQUENCE public.webhook_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.webhook_id_seq OWNED BY public.webhook.id;


CREATE TABLE public.webhookjob (
    job integer NOT NULL,
    webhook integer NOT NULL,
    job_type integer NOT NULL,
    json_data text NOT NULL
);


CREATE TABLE public.wikiname (
    id integer NOT NULL,
    person integer NOT NULL,
    wiki text NOT NULL,
    wikiname text NOT NULL
);


CREATE SEQUENCE public.wikiname_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wikiname_id_seq OWNED BY public.wikiname.id;


CREATE TABLE public.xref (
    from_type text NOT NULL,
    from_id text NOT NULL,
    from_id_int integer,
    to_type text NOT NULL,
    to_id text NOT NULL,
    to_id_int integer,
    creator integer,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    metadata text
);


ALTER TABLE ONLY public.accessartifact ALTER COLUMN id SET DEFAULT nextval('public.accessartifact_id_seq'::regclass);


ALTER TABLE ONLY public.accesspolicy ALTER COLUMN id SET DEFAULT nextval('public.accesspolicy_id_seq'::regclass);


ALTER TABLE ONLY public.accesspolicygrantflat ALTER COLUMN id SET DEFAULT nextval('public.accesspolicygrantflat_id_seq'::regclass);


ALTER TABLE ONLY public.account ALTER COLUMN id SET DEFAULT nextval('public.account_id_seq'::regclass);


ALTER TABLE ONLY public.announcement ALTER COLUMN id SET DEFAULT nextval('public.announcement_id_seq'::regclass);


ALTER TABLE ONLY public.answercontact ALTER COLUMN id SET DEFAULT nextval('public.answercontact_id_seq'::regclass);


ALTER TABLE ONLY public.apportjob ALTER COLUMN id SET DEFAULT nextval('public.apportjob_id_seq'::regclass);


ALTER TABLE ONLY public.archive ALTER COLUMN id SET DEFAULT nextval('public.archive_id_seq'::regclass);


ALTER TABLE ONLY public.archivearch ALTER COLUMN id SET DEFAULT nextval('public.archivearch_id_seq'::regclass);


ALTER TABLE ONLY public.archiveauthtoken ALTER COLUMN id SET DEFAULT nextval('public.archiveauthtoken_id_seq'::regclass);


ALTER TABLE ONLY public.archivedependency ALTER COLUMN id SET DEFAULT nextval('public.archivedependency_id_seq'::regclass);


ALTER TABLE ONLY public.archivefile ALTER COLUMN id SET DEFAULT nextval('public.archivefile_id_seq'::regclass);


ALTER TABLE ONLY public.archivejob ALTER COLUMN id SET DEFAULT nextval('public.archivejob_id_seq'::regclass);


ALTER TABLE ONLY public.archivepermission ALTER COLUMN id SET DEFAULT nextval('public.archivepermission_id_seq'::regclass);


ALTER TABLE ONLY public.archivesubscriber ALTER COLUMN id SET DEFAULT nextval('public.archivesubscriber_id_seq'::regclass);


ALTER TABLE ONLY public.binarypackagebuild ALTER COLUMN id SET DEFAULT nextval('public.binarypackagebuild_id_seq'::regclass);


ALTER TABLE ONLY public.binarypackagename ALTER COLUMN id SET DEFAULT nextval('public.binarypackagename_id_seq'::regclass);


ALTER TABLE ONLY public.binarypackagepublishinghistory ALTER COLUMN id SET DEFAULT nextval('public.binarypackagepublishinghistory_id_seq'::regclass);


ALTER TABLE ONLY public.binarypackagerelease ALTER COLUMN id SET DEFAULT nextval('public.binarypackagerelease_id_seq'::regclass);


ALTER TABLE ONLY public.binarypackagereleasedownloadcount ALTER COLUMN id SET DEFAULT nextval('public.binarypackagereleasedownloadcount_id_seq'::regclass);


ALTER TABLE ONLY public.branch ALTER COLUMN id SET DEFAULT nextval('public.branch_id_seq'::regclass);


ALTER TABLE ONLY public.branchjob ALTER COLUMN id SET DEFAULT nextval('public.branchjob_id_seq'::regclass);


ALTER TABLE ONLY public.branchmergeproposal ALTER COLUMN id SET DEFAULT nextval('public.branchmergeproposal_id_seq'::regclass);


ALTER TABLE ONLY public.branchmergeproposaljob ALTER COLUMN id SET DEFAULT nextval('public.branchmergeproposaljob_id_seq'::regclass);


ALTER TABLE ONLY public.branchsubscription ALTER COLUMN id SET DEFAULT nextval('public.branchsubscription_id_seq'::regclass);


ALTER TABLE ONLY public.bug ALTER COLUMN id SET DEFAULT nextval('public.bug_id_seq'::regclass);


ALTER TABLE ONLY public.bugactivity ALTER COLUMN id SET DEFAULT nextval('public.bugactivity_id_seq'::regclass);


ALTER TABLE ONLY public.bugaffectsperson ALTER COLUMN id SET DEFAULT nextval('public.bugaffectsperson_id_seq'::regclass);


ALTER TABLE ONLY public.bugattachment ALTER COLUMN id SET DEFAULT nextval('public.bugattachment_id_seq'::regclass);


ALTER TABLE ONLY public.bugbranch ALTER COLUMN id SET DEFAULT nextval('public.bugbranch_id_seq'::regclass);


ALTER TABLE ONLY public.bugmessage ALTER COLUMN id SET DEFAULT nextval('public.bugmessage_id_seq'::regclass);


ALTER TABLE ONLY public.bugnomination ALTER COLUMN id SET DEFAULT nextval('public.bugnomination_id_seq'::regclass);


ALTER TABLE ONLY public.bugnotification ALTER COLUMN id SET DEFAULT nextval('public.bugnotification_id_seq'::regclass);


ALTER TABLE ONLY public.bugnotificationattachment ALTER COLUMN id SET DEFAULT nextval('public.bugnotificationattachment_id_seq'::regclass);


ALTER TABLE ONLY public.bugnotificationrecipient ALTER COLUMN id SET DEFAULT nextval('public.bugnotificationrecipient_id_seq'::regclass);


ALTER TABLE ONLY public.bugsubscription ALTER COLUMN id SET DEFAULT nextval('public.bugsubscription_id_seq'::regclass);


ALTER TABLE ONLY public.bugsubscriptionfilter ALTER COLUMN id SET DEFAULT nextval('public.bugsubscriptionfilter_id_seq'::regclass);


ALTER TABLE ONLY public.bugsubscriptionfiltertag ALTER COLUMN id SET DEFAULT nextval('public.bugsubscriptionfiltertag_id_seq'::regclass);


ALTER TABLE ONLY public.bugsummary ALTER COLUMN id SET DEFAULT nextval('public.bugsummary_id_seq'::regclass);


ALTER TABLE ONLY public.bugsummaryjournal ALTER COLUMN id SET DEFAULT nextval('public.bugsummaryjournal_id_seq'::regclass);


ALTER TABLE ONLY public.bugtag ALTER COLUMN id SET DEFAULT nextval('public.bugtag_id_seq'::regclass);


ALTER TABLE ONLY public.bugtask ALTER COLUMN id SET DEFAULT nextval('public.bugtask_id_seq'::regclass);


ALTER TABLE ONLY public.bugtracker ALTER COLUMN id SET DEFAULT nextval('public.bugtracker_id_seq'::regclass);


ALTER TABLE ONLY public.bugtrackeralias ALTER COLUMN id SET DEFAULT nextval('public.bugtrackeralias_id_seq'::regclass);


ALTER TABLE ONLY public.bugtrackercomponent ALTER COLUMN id SET DEFAULT nextval('public.bugtrackercomponent_id_seq'::regclass);


ALTER TABLE ONLY public.bugtrackercomponentgroup ALTER COLUMN id SET DEFAULT nextval('public.bugtrackercomponentgroup_id_seq'::regclass);


ALTER TABLE ONLY public.bugtrackerperson ALTER COLUMN id SET DEFAULT nextval('public.bugtrackerperson_id_seq'::regclass);


ALTER TABLE ONLY public.bugwatch ALTER COLUMN id SET DEFAULT nextval('public.bugwatch_id_seq'::regclass);


ALTER TABLE ONLY public.bugwatchactivity ALTER COLUMN id SET DEFAULT nextval('public.bugwatchactivity_id_seq'::regclass);


ALTER TABLE ONLY public.builder ALTER COLUMN id SET DEFAULT nextval('public.builder_id_seq'::regclass);


ALTER TABLE ONLY public.buildfarmjob ALTER COLUMN id SET DEFAULT nextval('public.buildfarmjob_id_seq'::regclass);


ALTER TABLE ONLY public.buildqueue ALTER COLUMN id SET DEFAULT nextval('public.buildqueue_id_seq'::regclass);


ALTER TABLE ONLY public.codeimport ALTER COLUMN id SET DEFAULT nextval('public.codeimport_id_seq'::regclass);


ALTER TABLE ONLY public.codeimportevent ALTER COLUMN id SET DEFAULT nextval('public.codeimportevent_id_seq'::regclass);


ALTER TABLE ONLY public.codeimporteventdata ALTER COLUMN id SET DEFAULT nextval('public.codeimporteventdata_id_seq'::regclass);


ALTER TABLE ONLY public.codeimportjob ALTER COLUMN id SET DEFAULT nextval('public.codeimportjob_id_seq'::regclass);


ALTER TABLE ONLY public.codeimportmachine ALTER COLUMN id SET DEFAULT nextval('public.codeimportmachine_id_seq'::regclass);


ALTER TABLE ONLY public.codeimportresult ALTER COLUMN id SET DEFAULT nextval('public.codeimportresult_id_seq'::regclass);


ALTER TABLE ONLY public.codereviewmessage ALTER COLUMN id SET DEFAULT nextval('public.codereviewmessage_id_seq'::regclass);


ALTER TABLE ONLY public.codereviewvote ALTER COLUMN id SET DEFAULT nextval('public.codereviewvote_id_seq'::regclass);


ALTER TABLE ONLY public.commercialsubscription ALTER COLUMN id SET DEFAULT nextval('public.commercialsubscription_id_seq'::regclass);


ALTER TABLE ONLY public.component ALTER COLUMN id SET DEFAULT nextval('public.component_id_seq'::regclass);


ALTER TABLE ONLY public.componentselection ALTER COLUMN id SET DEFAULT nextval('public.componentselection_id_seq'::regclass);


ALTER TABLE ONLY public.continent ALTER COLUMN id SET DEFAULT nextval('public.continent_id_seq'::regclass);


ALTER TABLE ONLY public.country ALTER COLUMN id SET DEFAULT nextval('public.country_id_seq'::regclass);


ALTER TABLE ONLY public.customlanguagecode ALTER COLUMN id SET DEFAULT nextval('public.customlanguagecode_id_seq'::regclass);


ALTER TABLE ONLY public.cve ALTER COLUMN id SET DEFAULT nextval('public.cve_id_seq'::regclass);


ALTER TABLE ONLY public.cvereference ALTER COLUMN id SET DEFAULT nextval('public.cvereference_id_seq'::regclass);


ALTER TABLE ONLY public.diff ALTER COLUMN id SET DEFAULT nextval('public.diff_id_seq'::regclass);


ALTER TABLE ONLY public.distribution ALTER COLUMN id SET DEFAULT nextval('public.distribution_id_seq'::regclass);


ALTER TABLE ONLY public.distributionjob ALTER COLUMN id SET DEFAULT nextval('public.distributionjob_id_seq'::regclass);


ALTER TABLE ONLY public.distributionmirror ALTER COLUMN id SET DEFAULT nextval('public.distributionmirror_id_seq'::regclass);


ALTER TABLE ONLY public.distributionsourcepackage ALTER COLUMN id SET DEFAULT nextval('public.distributionsourcepackage_id_seq'::regclass);


ALTER TABLE ONLY public.distributionsourcepackagecache ALTER COLUMN id SET DEFAULT nextval('public.distributionsourcepackagecache_id_seq'::regclass);


ALTER TABLE ONLY public.distroarchseries ALTER COLUMN id SET DEFAULT nextval('public.distroarchseries_id_seq'::regclass);


ALTER TABLE ONLY public.distroseries ALTER COLUMN id SET DEFAULT nextval('public.distroseries_id_seq'::regclass);


ALTER TABLE ONLY public.distroseriesdifference ALTER COLUMN id SET DEFAULT nextval('public.distroseriesdifference_id_seq'::regclass);


ALTER TABLE ONLY public.distroseriesdifferencemessage ALTER COLUMN id SET DEFAULT nextval('public.distroseriesdifferencemessage_id_seq'::regclass);


ALTER TABLE ONLY public.distroserieslanguage ALTER COLUMN id SET DEFAULT nextval('public.distroserieslanguage_id_seq'::regclass);


ALTER TABLE ONLY public.distroseriespackagecache ALTER COLUMN id SET DEFAULT nextval('public.distroseriespackagecache_id_seq'::regclass);


ALTER TABLE ONLY public.distroseriesparent ALTER COLUMN id SET DEFAULT nextval('public.distroseriesparent_id_seq'::regclass);


ALTER TABLE ONLY public.emailaddress ALTER COLUMN id SET DEFAULT nextval('public.emailaddress_id_seq'::regclass);


ALTER TABLE ONLY public.faq ALTER COLUMN id SET DEFAULT nextval('public.faq_id_seq'::regclass);


ALTER TABLE ONLY public.featuredproject ALTER COLUMN id SET DEFAULT nextval('public.featuredproject_id_seq'::regclass);


ALTER TABLE ONLY public.featureflagchangelogentry ALTER COLUMN id SET DEFAULT nextval('public.featureflagchangelogentry_id_seq'::regclass);


ALTER TABLE ONLY public.flatpackagesetinclusion ALTER COLUMN id SET DEFAULT nextval('public.flatpackagesetinclusion_id_seq'::regclass);


ALTER TABLE ONLY public.fticache ALTER COLUMN id SET DEFAULT nextval('public.fticache_id_seq'::regclass);


ALTER TABLE ONLY public.gitactivity ALTER COLUMN id SET DEFAULT nextval('public.gitactivity_id_seq'::regclass);


ALTER TABLE ONLY public.gitrepository ALTER COLUMN id SET DEFAULT nextval('public.gitrepository_id_seq'::regclass);


ALTER TABLE ONLY public.gitrule ALTER COLUMN id SET DEFAULT nextval('public.gitrule_id_seq'::regclass);


ALTER TABLE ONLY public.gitrulegrant ALTER COLUMN id SET DEFAULT nextval('public.gitrulegrant_id_seq'::regclass);


ALTER TABLE ONLY public.gitsubscription ALTER COLUMN id SET DEFAULT nextval('public.gitsubscription_id_seq'::regclass);


ALTER TABLE ONLY public.gpgkey ALTER COLUMN id SET DEFAULT nextval('public.gpgkey_id_seq'::regclass);


ALTER TABLE ONLY public.hwdevice ALTER COLUMN id SET DEFAULT nextval('public.hwdevice_id_seq'::regclass);


ALTER TABLE ONLY public.hwdeviceclass ALTER COLUMN id SET DEFAULT nextval('public.hwdeviceclass_id_seq'::regclass);


ALTER TABLE ONLY public.hwdevicedriverlink ALTER COLUMN id SET DEFAULT nextval('public.hwdevicedriverlink_id_seq'::regclass);


ALTER TABLE ONLY public.hwdevicenamevariant ALTER COLUMN id SET DEFAULT nextval('public.hwdevicenamevariant_id_seq'::regclass);


ALTER TABLE ONLY public.hwdmihandle ALTER COLUMN id SET DEFAULT nextval('public.hwdmihandle_id_seq'::regclass);


ALTER TABLE ONLY public.hwdmivalue ALTER COLUMN id SET DEFAULT nextval('public.hwdmivalue_id_seq'::regclass);


ALTER TABLE ONLY public.hwdriver ALTER COLUMN id SET DEFAULT nextval('public.hwdriver_id_seq'::regclass);


ALTER TABLE ONLY public.hwsubmission ALTER COLUMN id SET DEFAULT nextval('public.hwsubmission_id_seq'::regclass);


ALTER TABLE ONLY public.hwsubmissionbug ALTER COLUMN id SET DEFAULT nextval('public.hwsubmissionbug_id_seq'::regclass);


ALTER TABLE ONLY public.hwsubmissiondevice ALTER COLUMN id SET DEFAULT nextval('public.hwsubmissiondevice_id_seq'::regclass);


ALTER TABLE ONLY public.hwsystemfingerprint ALTER COLUMN id SET DEFAULT nextval('public.hwsystemfingerprint_id_seq'::regclass);


ALTER TABLE ONLY public.hwtest ALTER COLUMN id SET DEFAULT nextval('public.hwtest_id_seq'::regclass);


ALTER TABLE ONLY public.hwtestanswer ALTER COLUMN id SET DEFAULT nextval('public.hwtestanswer_id_seq'::regclass);


ALTER TABLE ONLY public.hwtestanswerchoice ALTER COLUMN id SET DEFAULT nextval('public.hwtestanswerchoice_id_seq'::regclass);


ALTER TABLE ONLY public.hwtestanswercount ALTER COLUMN id SET DEFAULT nextval('public.hwtestanswercount_id_seq'::regclass);


ALTER TABLE ONLY public.hwtestanswercountdevice ALTER COLUMN id SET DEFAULT nextval('public.hwtestanswercountdevice_id_seq'::regclass);


ALTER TABLE ONLY public.hwtestanswerdevice ALTER COLUMN id SET DEFAULT nextval('public.hwtestanswerdevice_id_seq'::regclass);


ALTER TABLE ONLY public.hwvendorid ALTER COLUMN id SET DEFAULT nextval('public.hwvendorid_id_seq'::regclass);


ALTER TABLE ONLY public.hwvendorname ALTER COLUMN id SET DEFAULT nextval('public.hwvendorname_id_seq'::regclass);


ALTER TABLE ONLY public.incrementaldiff ALTER COLUMN id SET DEFAULT nextval('public.incrementaldiff_id_seq'::regclass);


ALTER TABLE ONLY public.ircid ALTER COLUMN id SET DEFAULT nextval('public.ircid_id_seq'::regclass);


ALTER TABLE ONLY public.jabberid ALTER COLUMN id SET DEFAULT nextval('public.jabberid_id_seq'::regclass);


ALTER TABLE ONLY public.job ALTER COLUMN id SET DEFAULT nextval('public.job_id_seq'::regclass);


ALTER TABLE ONLY public.karma ALTER COLUMN id SET DEFAULT nextval('public.karma_id_seq'::regclass);


ALTER TABLE ONLY public.karmaaction ALTER COLUMN id SET DEFAULT nextval('public.karmaaction_id_seq'::regclass);


ALTER TABLE ONLY public.karmacache ALTER COLUMN id SET DEFAULT nextval('public.karmacache_id_seq'::regclass);


ALTER TABLE ONLY public.karmacategory ALTER COLUMN id SET DEFAULT nextval('public.karmacategory_id_seq'::regclass);


ALTER TABLE ONLY public.karmatotalcache ALTER COLUMN id SET DEFAULT nextval('public.karmatotalcache_id_seq'::regclass);


ALTER TABLE ONLY public.language ALTER COLUMN id SET DEFAULT nextval('public.language_id_seq'::regclass);


ALTER TABLE ONLY public.languagepack ALTER COLUMN id SET DEFAULT nextval('public.languagepack_id_seq'::regclass);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache ALTER COLUMN id SET DEFAULT nextval('public.latestpersonsourcepackagereleasecache_id_seq'::regclass);


ALTER TABLE ONLY public.launchpaddatabaseupdatelog ALTER COLUMN id SET DEFAULT nextval('public.launchpaddatabaseupdatelog_id_seq'::regclass);


ALTER TABLE ONLY public.launchpadstatistic ALTER COLUMN id SET DEFAULT nextval('public.launchpadstatistic_id_seq'::regclass);


ALTER TABLE ONLY public.libraryfilealias ALTER COLUMN id SET DEFAULT nextval('public.libraryfilealias_id_seq'::regclass);


ALTER TABLE ONLY public.libraryfilecontent ALTER COLUMN id SET DEFAULT nextval('public.libraryfilecontent_id_seq'::regclass);


ALTER TABLE ONLY public.libraryfiledownloadcount ALTER COLUMN id SET DEFAULT nextval('public.libraryfiledownloadcount_id_seq'::regclass);


ALTER TABLE ONLY public.livefs ALTER COLUMN id SET DEFAULT nextval('public.livefs_id_seq'::regclass);


ALTER TABLE ONLY public.livefsbuild ALTER COLUMN id SET DEFAULT nextval('public.livefsbuild_id_seq'::regclass);


ALTER TABLE ONLY public.livefsfile ALTER COLUMN id SET DEFAULT nextval('public.livefsfile_id_seq'::regclass);


ALTER TABLE ONLY public.logintoken ALTER COLUMN id SET DEFAULT nextval('public.logintoken_id_seq'::regclass);


ALTER TABLE ONLY public.mailinglist ALTER COLUMN id SET DEFAULT nextval('public.mailinglist_id_seq'::regclass);


ALTER TABLE ONLY public.mailinglistsubscription ALTER COLUMN id SET DEFAULT nextval('public.mailinglistsubscription_id_seq'::regclass);


ALTER TABLE ONLY public.message ALTER COLUMN id SET DEFAULT nextval('public.message_id_seq'::regclass);


ALTER TABLE ONLY public.messageapproval ALTER COLUMN id SET DEFAULT nextval('public.messageapproval_id_seq'::regclass);


ALTER TABLE ONLY public.messagechunk ALTER COLUMN id SET DEFAULT nextval('public.messagechunk_id_seq'::regclass);


ALTER TABLE ONLY public.milestone ALTER COLUMN id SET DEFAULT nextval('public.milestone_id_seq'::regclass);


ALTER TABLE ONLY public.milestonetag ALTER COLUMN id SET DEFAULT nextval('public.milestonetag_id_seq'::regclass);


ALTER TABLE ONLY public.mirrorcdimagedistroseries ALTER COLUMN id SET DEFAULT nextval('public.mirrorcdimagedistroseries_id_seq'::regclass);


ALTER TABLE ONLY public.mirrordistroarchseries ALTER COLUMN id SET DEFAULT nextval('public.mirrordistroarchseries_id_seq'::regclass);


ALTER TABLE ONLY public.mirrordistroseriessource ALTER COLUMN id SET DEFAULT nextval('public.mirrordistroseriessource_id_seq'::regclass);


ALTER TABLE ONLY public.mirrorproberecord ALTER COLUMN id SET DEFAULT nextval('public.mirrorproberecord_id_seq'::regclass);


ALTER TABLE ONLY public.nameblacklist ALTER COLUMN id SET DEFAULT nextval('public.nameblacklist_id_seq'::regclass);


ALTER TABLE ONLY public.oauthaccesstoken ALTER COLUMN id SET DEFAULT nextval('public.oauthaccesstoken_id_seq'::regclass);


ALTER TABLE ONLY public.oauthconsumer ALTER COLUMN id SET DEFAULT nextval('public.oauthconsumer_id_seq'::regclass);


ALTER TABLE ONLY public.oauthrequesttoken ALTER COLUMN id SET DEFAULT nextval('public.oauthrequesttoken_id_seq'::regclass);


ALTER TABLE ONLY public.officialbugtag ALTER COLUMN id SET DEFAULT nextval('public.officialbugtag_id_seq'::regclass);


ALTER TABLE ONLY public.packagecopyjob ALTER COLUMN id SET DEFAULT nextval('public.packagecopyjob_id_seq'::regclass);


ALTER TABLE ONLY public.packagecopyrequest ALTER COLUMN id SET DEFAULT nextval('public.packagecopyrequest_id_seq'::regclass);


ALTER TABLE ONLY public.packagediff ALTER COLUMN id SET DEFAULT nextval('public.packagediff_id_seq'::regclass);


ALTER TABLE ONLY public.packageset ALTER COLUMN id SET DEFAULT nextval('public.packageset_id_seq'::regclass);


ALTER TABLE ONLY public.packagesetgroup ALTER COLUMN id SET DEFAULT nextval('public.packagesetgroup_id_seq'::regclass);


ALTER TABLE ONLY public.packagesetinclusion ALTER COLUMN id SET DEFAULT nextval('public.packagesetinclusion_id_seq'::regclass);


ALTER TABLE ONLY public.packagesetsources ALTER COLUMN id SET DEFAULT nextval('public.packagesetsources_id_seq'::regclass);


ALTER TABLE ONLY public.packageupload ALTER COLUMN id SET DEFAULT nextval('public.packageupload_id_seq'::regclass);


ALTER TABLE ONLY public.packageuploadbuild ALTER COLUMN id SET DEFAULT nextval('public.packageuploadbuild_id_seq'::regclass);


ALTER TABLE ONLY public.packageuploadcustom ALTER COLUMN id SET DEFAULT nextval('public.packageuploadcustom_id_seq'::regclass);


ALTER TABLE ONLY public.packageuploadsource ALTER COLUMN id SET DEFAULT nextval('public.packageuploadsource_id_seq'::regclass);


ALTER TABLE ONLY public.packagingjob ALTER COLUMN id SET DEFAULT nextval('public.packagingjob_id_seq'::regclass);


ALTER TABLE ONLY public.parsedapachelog ALTER COLUMN id SET DEFAULT nextval('public.parsedapachelog_id_seq'::regclass);


ALTER TABLE ONLY public.person ALTER COLUMN id SET DEFAULT nextval('public.person_id_seq'::regclass);


ALTER TABLE ONLY public.personlanguage ALTER COLUMN id SET DEFAULT nextval('public.personlanguage_id_seq'::regclass);


ALTER TABLE ONLY public.personlocation ALTER COLUMN id SET DEFAULT nextval('public.personlocation_id_seq'::regclass);


ALTER TABLE ONLY public.personnotification ALTER COLUMN id SET DEFAULT nextval('public.personnotification_id_seq'::regclass);


ALTER TABLE ONLY public.persontransferjob ALTER COLUMN id SET DEFAULT nextval('public.persontransferjob_id_seq'::regclass);


ALTER TABLE ONLY public.pillarname ALTER COLUMN id SET DEFAULT nextval('public.pillarname_id_seq'::regclass);


ALTER TABLE ONLY public.pocketchroot ALTER COLUMN id SET DEFAULT nextval('public.pocketchroot_id_seq'::regclass);


ALTER TABLE ONLY public.poexportrequest ALTER COLUMN id SET DEFAULT nextval('public.poexportrequest_id_seq'::regclass);


ALTER TABLE ONLY public.pofile ALTER COLUMN id SET DEFAULT nextval('public.pofile_id_seq'::regclass);


ALTER TABLE ONLY public.pofiletranslator ALTER COLUMN id SET DEFAULT nextval('public.pofiletranslator_id_seq'::regclass);


ALTER TABLE ONLY public.poll ALTER COLUMN id SET DEFAULT nextval('public.poll_id_seq'::regclass);


ALTER TABLE ONLY public.polloption ALTER COLUMN id SET DEFAULT nextval('public.polloption_id_seq'::regclass);


ALTER TABLE ONLY public.pomsgid ALTER COLUMN id SET DEFAULT nextval('public.pomsgid_id_seq'::regclass);


ALTER TABLE ONLY public.potemplate ALTER COLUMN id SET DEFAULT nextval('public.potemplate_id_seq'::regclass);


ALTER TABLE ONLY public.potmsgset ALTER COLUMN id SET DEFAULT nextval('public.potmsgset_id_seq'::regclass);


ALTER TABLE ONLY public.potranslation ALTER COLUMN id SET DEFAULT nextval('public.potranslation_id_seq'::regclass);


ALTER TABLE ONLY public.previewdiff ALTER COLUMN id SET DEFAULT nextval('public.previewdiff_id_seq'::regclass);


ALTER TABLE ONLY public.processor ALTER COLUMN id SET DEFAULT nextval('public.processor_id_seq'::regclass);


ALTER TABLE ONLY public.product ALTER COLUMN id SET DEFAULT nextval('public.product_id_seq'::regclass);


ALTER TABLE ONLY public.productjob ALTER COLUMN id SET DEFAULT nextval('public.productjob_id_seq'::regclass);


ALTER TABLE ONLY public.productlicense ALTER COLUMN id SET DEFAULT nextval('public.productlicense_id_seq'::regclass);


ALTER TABLE ONLY public.productrelease ALTER COLUMN id SET DEFAULT nextval('public.productrelease_id_seq'::regclass);


ALTER TABLE ONLY public.productseries ALTER COLUMN id SET DEFAULT nextval('public.productseries_id_seq'::regclass);


ALTER TABLE ONLY public.project ALTER COLUMN id SET DEFAULT nextval('public.project_id_seq'::regclass);


ALTER TABLE ONLY public.publisherconfig ALTER COLUMN id SET DEFAULT nextval('public.publisherconfig_id_seq'::regclass);


ALTER TABLE ONLY public.question ALTER COLUMN id SET DEFAULT nextval('public.question_id_seq'::regclass);


ALTER TABLE ONLY public.questionjob ALTER COLUMN id SET DEFAULT nextval('public.questionjob_id_seq'::regclass);


ALTER TABLE ONLY public.questionmessage ALTER COLUMN id SET DEFAULT nextval('public.questionmessage_id_seq'::regclass);


ALTER TABLE ONLY public.questionreopening ALTER COLUMN id SET DEFAULT nextval('public.questionreopening_id_seq'::regclass);


ALTER TABLE ONLY public.questionsubscription ALTER COLUMN id SET DEFAULT nextval('public.questionsubscription_id_seq'::regclass);


ALTER TABLE ONLY public.revision ALTER COLUMN id SET DEFAULT nextval('public.revision_id_seq'::regclass);


ALTER TABLE ONLY public.revisionauthor ALTER COLUMN id SET DEFAULT nextval('public.revisionauthor_id_seq'::regclass);


ALTER TABLE ONLY public.revisioncache ALTER COLUMN id SET DEFAULT nextval('public.revisioncache_id_seq'::regclass);


ALTER TABLE ONLY public.revisionparent ALTER COLUMN id SET DEFAULT nextval('public.revisionparent_id_seq'::regclass);


ALTER TABLE ONLY public.revisionproperty ALTER COLUMN id SET DEFAULT nextval('public.revisionproperty_id_seq'::regclass);


ALTER TABLE ONLY public.scriptactivity ALTER COLUMN id SET DEFAULT nextval('public.scriptactivity_id_seq'::regclass);


ALTER TABLE ONLY public.section ALTER COLUMN id SET DEFAULT nextval('public.section_id_seq'::regclass);


ALTER TABLE ONLY public.sectionselection ALTER COLUMN id SET DEFAULT nextval('public.sectionselection_id_seq'::regclass);


ALTER TABLE ONLY public.seriessourcepackagebranch ALTER COLUMN id SET DEFAULT nextval('public.seriessourcepackagebranch_id_seq'::regclass);


ALTER TABLE ONLY public.sharingjob ALTER COLUMN id SET DEFAULT nextval('public.sharingjob_id_seq'::regclass);


ALTER TABLE ONLY public.signedcodeofconduct ALTER COLUMN id SET DEFAULT nextval('public.signedcodeofconduct_id_seq'::regclass);


ALTER TABLE ONLY public.snap ALTER COLUMN id SET DEFAULT nextval('public.snap_id_seq'::regclass);


ALTER TABLE ONLY public.snapbase ALTER COLUMN id SET DEFAULT nextval('public.snapbase_id_seq'::regclass);


ALTER TABLE ONLY public.snapbuild ALTER COLUMN id SET DEFAULT nextval('public.snapbuild_id_seq'::regclass);


ALTER TABLE ONLY public.snapfile ALTER COLUMN id SET DEFAULT nextval('public.snapfile_id_seq'::regclass);


ALTER TABLE ONLY public.snappydistroseries ALTER COLUMN id SET DEFAULT nextval('public.snappydistroseries_id_seq'::regclass);


ALTER TABLE ONLY public.snappyseries ALTER COLUMN id SET DEFAULT nextval('public.snappyseries_id_seq'::regclass);


ALTER TABLE ONLY public.sourcepackageformatselection ALTER COLUMN id SET DEFAULT nextval('public.sourcepackageformatselection_id_seq'::regclass);


ALTER TABLE ONLY public.sourcepackagename ALTER COLUMN id SET DEFAULT nextval('public.sourcepackagename_id_seq'::regclass);


ALTER TABLE ONLY public.sourcepackagepublishinghistory ALTER COLUMN id SET DEFAULT nextval('public.sourcepackagepublishinghistory_id_seq'::regclass);


ALTER TABLE ONLY public.sourcepackagerecipe ALTER COLUMN id SET DEFAULT nextval('public.sourcepackagerecipe_id_seq'::regclass);


ALTER TABLE ONLY public.sourcepackagerecipebuild ALTER COLUMN id SET DEFAULT nextval('public.sourcepackagerecipebuild_id_seq'::regclass);


ALTER TABLE ONLY public.sourcepackagerecipedata ALTER COLUMN id SET DEFAULT nextval('public.sourcepackagerecipedata_id_seq'::regclass);


ALTER TABLE ONLY public.sourcepackagerecipedatainstruction ALTER COLUMN id SET DEFAULT nextval('public.sourcepackagerecipedatainstruction_id_seq'::regclass);


ALTER TABLE ONLY public.sourcepackagerecipedistroseries ALTER COLUMN id SET DEFAULT nextval('public.sourcepackagerecipedistroseries_id_seq'::regclass);


ALTER TABLE ONLY public.sourcepackagerelease ALTER COLUMN id SET DEFAULT nextval('public.sourcepackagerelease_id_seq'::regclass);


ALTER TABLE ONLY public.specification ALTER COLUMN id SET DEFAULT nextval('public.specification_id_seq'::regclass);


ALTER TABLE ONLY public.specificationbranch ALTER COLUMN id SET DEFAULT nextval('public.specificationbranch_id_seq'::regclass);


ALTER TABLE ONLY public.specificationdependency ALTER COLUMN id SET DEFAULT nextval('public.specificationdependency_id_seq'::regclass);


ALTER TABLE ONLY public.specificationmessage ALTER COLUMN id SET DEFAULT nextval('public.specificationmessage_id_seq'::regclass);


ALTER TABLE ONLY public.specificationsubscription ALTER COLUMN id SET DEFAULT nextval('public.specificationsubscription_id_seq'::regclass);


ALTER TABLE ONLY public.specificationworkitem ALTER COLUMN id SET DEFAULT nextval('public.specificationworkitem_id_seq'::regclass);


ALTER TABLE ONLY public.sprint ALTER COLUMN id SET DEFAULT nextval('public.sprint_id_seq'::regclass);


ALTER TABLE ONLY public.sprintattendance ALTER COLUMN id SET DEFAULT nextval('public.sprintattendance_id_seq'::regclass);


ALTER TABLE ONLY public.sprintspecification ALTER COLUMN id SET DEFAULT nextval('public.sprintspecification_id_seq'::regclass);


ALTER TABLE ONLY public.sshkey ALTER COLUMN id SET DEFAULT nextval('public.sshkey_id_seq'::regclass);


ALTER TABLE ONLY public.structuralsubscription ALTER COLUMN id SET DEFAULT nextval('public.structuralsubscription_id_seq'::regclass);


ALTER TABLE ONLY public.teammembership ALTER COLUMN id SET DEFAULT nextval('public.teammembership_id_seq'::regclass);


ALTER TABLE ONLY public.teamparticipation ALTER COLUMN id SET DEFAULT nextval('public.teamparticipation_id_seq'::regclass);


ALTER TABLE ONLY public.temporaryblobstorage ALTER COLUMN id SET DEFAULT nextval('public.temporaryblobstorage_id_seq'::regclass);


ALTER TABLE ONLY public.translationgroup ALTER COLUMN id SET DEFAULT nextval('public.translationgroup_id_seq'::regclass);


ALTER TABLE ONLY public.translationimportqueueentry ALTER COLUMN id SET DEFAULT nextval('public.translationimportqueueentry_id_seq'::regclass);


ALTER TABLE ONLY public.translationmessage ALTER COLUMN id SET DEFAULT nextval('public.translationmessage_id_seq'::regclass);


ALTER TABLE ONLY public.translationrelicensingagreement ALTER COLUMN id SET DEFAULT nextval('public.translationrelicensingagreement_id_seq'::regclass);


ALTER TABLE ONLY public.translationtemplateitem ALTER COLUMN id SET DEFAULT nextval('public.translationtemplateitem_id_seq'::regclass);


ALTER TABLE ONLY public.translationtemplatesbuild ALTER COLUMN id SET DEFAULT nextval('public.translationtemplatesbuild_id_seq'::regclass);


ALTER TABLE ONLY public.translator ALTER COLUMN id SET DEFAULT nextval('public.translator_id_seq'::regclass);


ALTER TABLE ONLY public.usertouseremail ALTER COLUMN id SET DEFAULT nextval('public.usertouseremail_id_seq'::regclass);


ALTER TABLE ONLY public.vote ALTER COLUMN id SET DEFAULT nextval('public.vote_id_seq'::regclass);


ALTER TABLE ONLY public.votecast ALTER COLUMN id SET DEFAULT nextval('public.votecast_id_seq'::regclass);


ALTER TABLE ONLY public.webhook ALTER COLUMN id SET DEFAULT nextval('public.webhook_id_seq'::regclass);


ALTER TABLE ONLY public.wikiname ALTER COLUMN id SET DEFAULT nextval('public.wikiname_id_seq'::regclass);


ALTER TABLE ONLY public.accessartifact
    ADD CONSTRAINT accessartifact_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.accessartifactgrant
    ADD CONSTRAINT accessartifactgrant_pkey PRIMARY KEY (artifact, grantee);


ALTER TABLE ONLY public.accesspolicy
    ADD CONSTRAINT accesspolicy_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.accesspolicyartifact
    ADD CONSTRAINT accesspolicyartifact_pkey PRIMARY KEY (artifact, policy);


ALTER TABLE ONLY public.accesspolicygrant
    ADD CONSTRAINT accesspolicygrant_pkey PRIMARY KEY (policy, grantee);


ALTER TABLE ONLY public.accesspolicygrantflat
    ADD CONSTRAINT accesspolicygrantflat_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.announcement
    ADD CONSTRAINT announcement_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.apportjob
    ADD CONSTRAINT apportjob__job__key UNIQUE (job);


ALTER TABLE ONLY public.apportjob
    ADD CONSTRAINT apportjob_pkey PRIMARY KEY (id);

ALTER TABLE public.apportjob CLUSTER ON apportjob_pkey;


ALTER TABLE ONLY public.archive
    ADD CONSTRAINT archive_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.archivearch
    ADD CONSTRAINT archivearch__archive__processor__key UNIQUE (archive, processor);


ALTER TABLE ONLY public.archivearch
    ADD CONSTRAINT archivearch_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.archiveauthtoken
    ADD CONSTRAINT archiveauthtoken_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.archiveauthtoken
    ADD CONSTRAINT archiveauthtoken_token_key UNIQUE (token);


ALTER TABLE ONLY public.archivedependency
    ADD CONSTRAINT archivedependency__unique UNIQUE (archive, dependency);


ALTER TABLE ONLY public.archivedependency
    ADD CONSTRAINT archivedependency_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.archivefile
    ADD CONSTRAINT archivefile_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.archivejob
    ADD CONSTRAINT archivejob__job__key UNIQUE (job);


ALTER TABLE ONLY public.archivejob
    ADD CONSTRAINT archivejob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.archivepermission
    ADD CONSTRAINT archivepermission_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.archivesubscriber
    ADD CONSTRAINT archivesubscriber_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.revisionauthor
    ADD CONSTRAINT archuserid_archuserid_key UNIQUE (name);


ALTER TABLE ONLY public.revisionauthor
    ADD CONSTRAINT archuserid_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.binarypackagerelease
    ADD CONSTRAINT binarypackage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.binarypackagefile
    ADD CONSTRAINT binarypackagefile_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.binarypackagename
    ADD CONSTRAINT binarypackagename_name_key UNIQUE (name);


ALTER TABLE ONLY public.binarypackagename
    ADD CONSTRAINT binarypackagename_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_binarypackagename_key UNIQUE (binarypackagename, build, version);


ALTER TABLE ONLY public.binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_build_name_uniq UNIQUE (build, binarypackagename);


ALTER TABLE ONLY public.binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount__archive__binary_package_rele UNIQUE (archive, binary_package_release, day, country);


ALTER TABLE ONLY public.binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch__unique_name__key UNIQUE (unique_name);


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch_url_unique UNIQUE (url);


ALTER TABLE ONLY public.branchjob
    ADD CONSTRAINT branchjob_job_key UNIQUE (job);


ALTER TABLE ONLY public.branchjob
    ADD CONSTRAINT branchjob_pkey PRIMARY KEY (id);

ALTER TABLE public.branchjob CLUSTER ON branchjob_pkey;


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.branchmergeproposaljob
    ADD CONSTRAINT branchmergeproposaljob_job_key UNIQUE (job);


ALTER TABLE ONLY public.branchmergeproposaljob
    ADD CONSTRAINT branchmergeproposaljob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.branchsubscription
    ADD CONSTRAINT branchsubscription__person__branch__key UNIQUE (person, branch);


ALTER TABLE ONLY public.branchsubscription
    ADD CONSTRAINT branchsubscription_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugbranch
    ADD CONSTRAINT bug_branch_unique UNIQUE (bug, branch);


ALTER TABLE ONLY public.bug
    ADD CONSTRAINT bug_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugactivity
    ADD CONSTRAINT bugactivity_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugaffectsperson
    ADD CONSTRAINT bugaffectsperson_bug_person_uniq UNIQUE (bug, person);


ALTER TABLE ONLY public.bugaffectsperson
    ADD CONSTRAINT bugaffectsperson_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugattachment
    ADD CONSTRAINT bugattachment_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugbranch
    ADD CONSTRAINT bugbranch_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugmessage
    ADD CONSTRAINT bugmessage__bug__index__key UNIQUE (bug, index);


ALTER TABLE ONLY public.bugmessage
    ADD CONSTRAINT bugmessage__bug__message__key UNIQUE (bug, message);


ALTER TABLE ONLY public.bugmessage
    ADD CONSTRAINT bugmessage__bugwatch__remote_comment_id__key UNIQUE (bugwatch, remote_comment_id);


ALTER TABLE ONLY public.bugmessage
    ADD CONSTRAINT bugmessage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugmute
    ADD CONSTRAINT bugmute_pkey PRIMARY KEY (person, bug);


ALTER TABLE ONLY public.bugnomination
    ADD CONSTRAINT bugnomination_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugnotification
    ADD CONSTRAINT bugnotification__bug__message__unq UNIQUE (bug, message);


ALTER TABLE ONLY public.bugnotification
    ADD CONSTRAINT bugnotification_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugnotificationarchive
    ADD CONSTRAINT bugnotificationarchive__bug__message__key UNIQUE (bug, message);


ALTER TABLE ONLY public.bugnotificationarchive
    ADD CONSTRAINT bugnotificationarchive_pk PRIMARY KEY (id);


ALTER TABLE ONLY public.bugnotificationattachment
    ADD CONSTRAINT bugnotificationattachment_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugnotificationfilter
    ADD CONSTRAINT bugnotificationfilter_pkey PRIMARY KEY (bug_notification, bug_subscription_filter);


ALTER TABLE ONLY public.bugnotificationrecipient
    ADD CONSTRAINT bugnotificationrecipient__bug_notificaion__person__key UNIQUE (bug_notification, person);


ALTER TABLE ONLY public.bugnotificationrecipient
    ADD CONSTRAINT bugnotificationrecipient_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugsubscription
    ADD CONSTRAINT bugsubscription_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugsubscriptionfilter
    ADD CONSTRAINT bugsubscriptionfilter_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugsubscriptionfilterimportance
    ADD CONSTRAINT bugsubscriptionfilterimportance_pkey PRIMARY KEY (filter, importance);


ALTER TABLE ONLY public.bugsubscriptionfiltermute
    ADD CONSTRAINT bugsubscriptionfiltermute_pkey PRIMARY KEY (person, filter);


ALTER TABLE ONLY public.bugsubscriptionfilterstatus
    ADD CONSTRAINT bugsubscriptionfilterstatus_pkey PRIMARY KEY (filter, status);


ALTER TABLE ONLY public.bugsubscriptionfiltertag
    ADD CONSTRAINT bugsubscriptionfiltertag_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugsubscriptionfilterinformationtype
    ADD CONSTRAINT bugsubscriptioninformationtype_pkey PRIMARY KEY (filter, information_type);


ALTER TABLE ONLY public.bugsummary
    ADD CONSTRAINT bugsummary_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugsummaryjournal
    ADD CONSTRAINT bugsummaryjournal_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugtracker
    ADD CONSTRAINT bugsystem_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugtag
    ADD CONSTRAINT bugtag__tag__bug__key UNIQUE (tag, bug);


ALTER TABLE ONLY public.bugtag
    ADD CONSTRAINT bugtag_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugtaskflat
    ADD CONSTRAINT bugtaskflat_pkey PRIMARY KEY (bugtask);


ALTER TABLE ONLY public.bugtrackeralias
    ADD CONSTRAINT bugtracker__base_url__key UNIQUE (base_url);


ALTER TABLE ONLY public.bugtrackeralias
    ADD CONSTRAINT bugtrackeralias_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugtrackercomponent
    ADD CONSTRAINT bugtrackercomponent__component_group__name__key UNIQUE (component_group, name);


ALTER TABLE ONLY public.bugtrackercomponent
    ADD CONSTRAINT bugtrackercomponent__disto__spn__key UNIQUE (distribution, source_package_name);


ALTER TABLE ONLY public.bugtrackercomponent
    ADD CONSTRAINT bugtrackercomponent_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugtrackercomponentgroup
    ADD CONSTRAINT bugtrackercomponentgroup__bug_tracker__name__key UNIQUE (bug_tracker, name);


ALTER TABLE ONLY public.bugtrackercomponentgroup
    ADD CONSTRAINT bugtrackercomponentgroup_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugtrackerperson
    ADD CONSTRAINT bugtrackerperson__bugtracker__name__key UNIQUE (bugtracker, name);


ALTER TABLE ONLY public.bugtrackerperson
    ADD CONSTRAINT bugtrackerperson_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugwatch
    ADD CONSTRAINT bugwatch_bugtask_target UNIQUE (id, bug);


ALTER TABLE ONLY public.bugwatch
    ADD CONSTRAINT bugwatch_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.bugwatchactivity
    ADD CONSTRAINT bugwatchactivity_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.builder
    ADD CONSTRAINT builder_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.builder
    ADD CONSTRAINT builder_url_key UNIQUE (url);


ALTER TABLE ONLY public.builderprocessor
    ADD CONSTRAINT builderprocessor_pkey PRIMARY KEY (builder, processor);


ALTER TABLE ONLY public.buildfarmjob
    ADD CONSTRAINT buildfarmjob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.buildqueue
    ADD CONSTRAINT buildqueue_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.revision
    ADD CONSTRAINT changeset_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.codeimport
    ADD CONSTRAINT codeimport_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.codeimportevent
    ADD CONSTRAINT codeimportevent_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.codeimporteventdata
    ADD CONSTRAINT codeimporteventdata__event__data_type__key UNIQUE (event, data_type);


ALTER TABLE ONLY public.codeimporteventdata
    ADD CONSTRAINT codeimporteventdata_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.codeimportjob
    ADD CONSTRAINT codeimportjob__code_import__key UNIQUE (code_import);


ALTER TABLE ONLY public.codeimportjob
    ADD CONSTRAINT codeimportjob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.codeimportmachine
    ADD CONSTRAINT codeimportmachine_hostname_key UNIQUE (hostname);


ALTER TABLE ONLY public.codeimportmachine
    ADD CONSTRAINT codeimportmachine_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.codeimportresult
    ADD CONSTRAINT codeimportresult_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.codereviewinlinecomment
    ADD CONSTRAINT codereviewinlinecomment_pkey PRIMARY KEY (comment);


ALTER TABLE ONLY public.codereviewinlinecommentdraft
    ADD CONSTRAINT codereviewinlinecommentdraft_pkey PRIMARY KEY (previewdiff, person);


ALTER TABLE ONLY public.codereviewmessage
    ADD CONSTRAINT codereviewmessage__branch_merge_proposal__id_key UNIQUE (branch_merge_proposal, id);


ALTER TABLE ONLY public.codereviewmessage
    ADD CONSTRAINT codereviewmessage_message_key UNIQUE (message);


ALTER TABLE ONLY public.codereviewmessage
    ADD CONSTRAINT codereviewmessage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.codereviewvote
    ADD CONSTRAINT codereviewvote_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.commercialsubscription
    ADD CONSTRAINT commercialsubscription_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.component
    ADD CONSTRAINT component_name_key UNIQUE (name);


ALTER TABLE ONLY public.component
    ADD CONSTRAINT component_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.componentselection
    ADD CONSTRAINT componentselection__distroseries__component__key UNIQUE (distroseries, component);


ALTER TABLE ONLY public.componentselection
    ADD CONSTRAINT componentselection_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.continent
    ADD CONSTRAINT continent_code_key UNIQUE (code);


ALTER TABLE ONLY public.continent
    ADD CONSTRAINT continent_name_key UNIQUE (name);


ALTER TABLE ONLY public.continent
    ADD CONSTRAINT continent_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.country
    ADD CONSTRAINT country_code2_uniq UNIQUE (iso3166code2);


ALTER TABLE ONLY public.country
    ADD CONSTRAINT country_code3_uniq UNIQUE (iso3166code3);


ALTER TABLE ONLY public.country
    ADD CONSTRAINT country_name_uniq UNIQUE (name);


ALTER TABLE ONLY public.country
    ADD CONSTRAINT country_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT creator__upload_archive__upload_distroseries__sourcepackagename UNIQUE (creator, upload_archive, upload_distroseries, sourcepackagename);


ALTER TABLE ONLY public.customlanguagecode
    ADD CONSTRAINT customlanguagecode_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.cve
    ADD CONSTRAINT cve_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.cve
    ADD CONSTRAINT cve_sequence_uniq UNIQUE (sequence);


ALTER TABLE ONLY public.cvereference
    ADD CONSTRAINT cvereference_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.databasecpustats
    ADD CONSTRAINT databasecpustats_pkey PRIMARY KEY (date_created, username);


ALTER TABLE ONLY public.databasediskutilization
    ADD CONSTRAINT databasediskutilization_pkey PRIMARY KEY (date_created, sort);


ALTER TABLE ONLY public.databasereplicationlag
    ADD CONSTRAINT databasereplicationlag_pkey PRIMARY KEY (node);


ALTER TABLE ONLY public.databasetablestats
    ADD CONSTRAINT databasetablestats_pkey PRIMARY KEY (date_created, schemaname, relname);

ALTER TABLE public.databasetablestats CLUSTER ON databasetablestats_pkey;


ALTER TABLE ONLY public.diff
    ADD CONSTRAINT diff_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution_name_key UNIQUE (name);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distributionjob
    ADD CONSTRAINT distributionjob__job__key UNIQUE (job);


ALTER TABLE ONLY public.distributionjob
    ADD CONSTRAINT distributionjob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distributionmirror
    ADD CONSTRAINT distributionmirror_ftp_base_url_key UNIQUE (ftp_base_url);


ALTER TABLE ONLY public.distributionmirror
    ADD CONSTRAINT distributionmirror_http_base_url_key UNIQUE (http_base_url);


ALTER TABLE ONLY public.distributionmirror
    ADD CONSTRAINT distributionmirror_name_key UNIQUE (name);


ALTER TABLE ONLY public.distributionmirror
    ADD CONSTRAINT distributionmirror_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distributionmirror
    ADD CONSTRAINT distributionmirror_rsync_base_url_key UNIQUE (rsync_base_url);


ALTER TABLE ONLY public.distributionsourcepackage
    ADD CONSTRAINT distributionpackage__sourcepackagename__distribution__key UNIQUE (sourcepackagename, distribution);

ALTER TABLE public.distributionsourcepackage CLUSTER ON distributionpackage__sourcepackagename__distribution__key;


ALTER TABLE ONLY public.distributionsourcepackage
    ADD CONSTRAINT distributionsourcepackage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache__distribution__sourcepackagename UNIQUE (distribution, sourcepackagename, archive);


ALTER TABLE ONLY public.distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distroarchseries
    ADD CONSTRAINT distroarchrelease_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distroarchseries
    ADD CONSTRAINT distroarchseries__architecturetag__distroseries__key UNIQUE (architecturetag, distroseries);


ALTER TABLE ONLY public.distroarchseries
    ADD CONSTRAINT distroarchseries__processor__distroseries__key UNIQUE (processor, distroseries);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distrorelease__distribution__name__key UNIQUE (distribution, name);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distrorelease_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distroserieslanguage
    ADD CONSTRAINT distroreleaselanguage_distrorelease_language_uniq UNIQUE (distroseries, language);


ALTER TABLE ONLY public.distroserieslanguage
    ADD CONSTRAINT distroreleaselanguage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distroseriespackagecache
    ADD CONSTRAINT distroreleasepackagecache_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packageupload
    ADD CONSTRAINT distroreleasequeue_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packageuploadbuild
    ADD CONSTRAINT distroreleasequeuebuild__distroreleasequeue__build__unique UNIQUE (packageupload, build);


ALTER TABLE ONLY public.packageuploadbuild
    ADD CONSTRAINT distroreleasequeuebuild_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packageuploadcustom
    ADD CONSTRAINT distroreleasequeuecustom_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packageuploadsource
    ADD CONSTRAINT distroreleasequeuesource_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distroseries__distribution__id__key UNIQUE (distribution, id);


ALTER TABLE ONLY public.distroseriesdifference
    ADD CONSTRAINT distroseriesdifference__derived_series__parent_series__source_p UNIQUE (derived_series, parent_series, source_package_name);


ALTER TABLE ONLY public.distroseriesdifference
    ADD CONSTRAINT distroseriesdifference_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distroseriesdifferencemessage
    ADD CONSTRAINT distroseriesdifferencemessage_message_key UNIQUE (message);


ALTER TABLE ONLY public.distroseriesdifferencemessage
    ADD CONSTRAINT distroseriesdifferencemessage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.distroseriespackagecache
    ADD CONSTRAINT distroseriespackagecache__distroseries__binarypackagename__arch UNIQUE (distroseries, binarypackagename, archive);


ALTER TABLE ONLY public.distroseriesparent
    ADD CONSTRAINT distroseriesparent_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.emailaddress
    ADD CONSTRAINT emailaddress_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.faq
    ADD CONSTRAINT faq_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.featureflag
    ADD CONSTRAINT feature_flag_pkey PRIMARY KEY (scope, flag);


ALTER TABLE ONLY public.featureflag
    ADD CONSTRAINT feature_flag_unique_priority_per_flag UNIQUE (flag, priority);


ALTER TABLE ONLY public.featuredproject
    ADD CONSTRAINT featuredproject_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.featureflagchangelogentry
    ADD CONSTRAINT featureflagchangelogentry_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.flatpackagesetinclusion
    ADD CONSTRAINT flatpackagesetinclusion__parent__child__key UNIQUE (parent, child);


ALTER TABLE ONLY public.flatpackagesetinclusion
    ADD CONSTRAINT flatpackagesetinclusion_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.fticache
    ADD CONSTRAINT fticache_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.fticache
    ADD CONSTRAINT fticache_tablename_key UNIQUE (tablename);


ALTER TABLE ONLY public.garbojobstate
    ADD CONSTRAINT garbojobstate_pkey PRIMARY KEY (name);


ALTER TABLE ONLY public.gitactivity
    ADD CONSTRAINT gitactivity_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.gitjob
    ADD CONSTRAINT gitjob_pkey PRIMARY KEY (job);


ALTER TABLE ONLY public.gitref
    ADD CONSTRAINT gitref_pkey PRIMARY KEY (repository, path);


ALTER TABLE ONLY public.gitrepository
    ADD CONSTRAINT gitrepository_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.gitrule
    ADD CONSTRAINT gitrule__repository__id__key UNIQUE (repository, id);


ALTER TABLE ONLY public.gitrule
    ADD CONSTRAINT gitrule__repository__position__key UNIQUE (repository, "position") DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.gitrule
    ADD CONSTRAINT gitrule__repository__ref_pattern__key UNIQUE (repository, ref_pattern);


ALTER TABLE ONLY public.gitrule
    ADD CONSTRAINT gitrule_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.gitrulegrant
    ADD CONSTRAINT gitrulegrant_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.gitsubscription
    ADD CONSTRAINT gitsubscription_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.gpgkey
    ADD CONSTRAINT gpgkey_fingerprint_key UNIQUE (fingerprint);


ALTER TABLE ONLY public.gpgkey
    ADD CONSTRAINT gpgkey_owner_key UNIQUE (owner, id);


ALTER TABLE ONLY public.gpgkey
    ADD CONSTRAINT gpgkey_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwdevice
    ADD CONSTRAINT hwdevice__bus_vendor_id__bus_product_id__variant__key UNIQUE (bus_vendor_id, bus_product_id, variant);


ALTER TABLE ONLY public.hwdevice
    ADD CONSTRAINT hwdevice_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwdeviceclass
    ADD CONSTRAINT hwdeviceclass_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwdevicedriverlink
    ADD CONSTRAINT hwdevicedriverlink_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwdevicenamevariant
    ADD CONSTRAINT hwdevicenamevariant__vendor_name__product_name__device__key UNIQUE (vendor_name, product_name, device);


ALTER TABLE ONLY public.hwdevicenamevariant
    ADD CONSTRAINT hwdevicenamevariant_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwdmihandle
    ADD CONSTRAINT hwdmihandle_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwdmivalue
    ADD CONSTRAINT hwdmivalue_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwdriver
    ADD CONSTRAINT hwdriver__package_name__name__key UNIQUE (package_name, name);


ALTER TABLE ONLY public.hwdriver
    ADD CONSTRAINT hwdriver_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwsubmission
    ADD CONSTRAINT hwsubmission__submission_key__key UNIQUE (submission_key);


ALTER TABLE ONLY public.hwsubmission
    ADD CONSTRAINT hwsubmission_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwsubmissionbug
    ADD CONSTRAINT hwsubmissionbug__submission__bug__key UNIQUE (submission, bug);


ALTER TABLE ONLY public.hwsubmissionbug
    ADD CONSTRAINT hwsubmissionbug_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwsubmissiondevice
    ADD CONSTRAINT hwsubmissiondevice_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwsystemfingerprint
    ADD CONSTRAINT hwsystemfingerprint__fingerprint__key UNIQUE (fingerprint);


ALTER TABLE ONLY public.hwsystemfingerprint
    ADD CONSTRAINT hwsystemfingerprint_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwtest
    ADD CONSTRAINT hwtest_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwtestanswer
    ADD CONSTRAINT hwtestanswer_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwtestanswerchoice
    ADD CONSTRAINT hwtestanswerchoice__choice__test__key UNIQUE (choice, test);


ALTER TABLE ONLY public.hwtestanswerchoice
    ADD CONSTRAINT hwtestanswerchoice__test__id__key UNIQUE (test, id);


ALTER TABLE ONLY public.hwtestanswerchoice
    ADD CONSTRAINT hwtestanswerchoice_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwtestanswercount
    ADD CONSTRAINT hwtestanswercount_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwtestanswercountdevice
    ADD CONSTRAINT hwtestanswercountdevice__answer__device_driver__key UNIQUE (answer, device_driver);


ALTER TABLE ONLY public.hwtestanswercountdevice
    ADD CONSTRAINT hwtestanswercountdevice_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwtestanswerdevice
    ADD CONSTRAINT hwtestanswerdevice__answer__device_driver__key UNIQUE (answer, device_driver);


ALTER TABLE ONLY public.hwtestanswerdevice
    ADD CONSTRAINT hwtestanswerdevice_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwvendorid
    ADD CONSTRAINT hwvendorid__bus_vendor_id__vendor_name__key UNIQUE (bus, vendor_id_for_bus, vendor_name);


ALTER TABLE ONLY public.hwvendorid
    ADD CONSTRAINT hwvendorid_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.hwvendorname
    ADD CONSTRAINT hwvendorname_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.incrementaldiff
    ADD CONSTRAINT incrementaldiff_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.ircid
    ADD CONSTRAINT ircid_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.jabberid
    ADD CONSTRAINT jabberid_jabberid_key UNIQUE (jabberid);


ALTER TABLE ONLY public.jabberid
    ADD CONSTRAINT jabberid_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.job
    ADD CONSTRAINT job__status__id__key UNIQUE (status, id);


ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_pkey PRIMARY KEY (id);

ALTER TABLE public.job CLUSTER ON job_pkey;


ALTER TABLE ONLY public.karma
    ADD CONSTRAINT karma_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.karmaaction
    ADD CONSTRAINT karmaaction_name_uniq UNIQUE (name);


ALTER TABLE ONLY public.karmaaction
    ADD CONSTRAINT karmaaction_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.karmacache
    ADD CONSTRAINT karmacache_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.karmacategory
    ADD CONSTRAINT karmacategory_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.karmatotalcache
    ADD CONSTRAINT karmatotalcache_person_key UNIQUE (person);


ALTER TABLE ONLY public.karmatotalcache
    ADD CONSTRAINT karmatotalcache_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.language
    ADD CONSTRAINT language_code_key UNIQUE (code);


ALTER TABLE ONLY public.language
    ADD CONSTRAINT language_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.languagepack
    ADD CONSTRAINT languagepack_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT latestpersonsourcepackagereleasecache_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.launchpaddatabaserevision
    ADD CONSTRAINT launchpaddatabaserevision_pkey PRIMARY KEY (major, minor, patch);


ALTER TABLE ONLY public.launchpaddatabaseupdatelog
    ADD CONSTRAINT launchpaddatabaseupdatelog_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.launchpadstatistic
    ADD CONSTRAINT launchpadstatistic_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.launchpadstatistic
    ADD CONSTRAINT launchpadstatistics_uniq_name UNIQUE (name);


ALTER TABLE ONLY public.libraryfilealias
    ADD CONSTRAINT libraryfilealias_pkey PRIMARY KEY (id);

ALTER TABLE public.libraryfilealias CLUSTER ON libraryfilealias_pkey;


ALTER TABLE ONLY public.libraryfilecontent
    ADD CONSTRAINT libraryfilecontent_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.libraryfiledownloadcount
    ADD CONSTRAINT libraryfiledownloadcount__libraryfilealias__day__country__key UNIQUE (libraryfilealias, day, country);


ALTER TABLE ONLY public.libraryfiledownloadcount
    ADD CONSTRAINT libraryfiledownloadcount_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.livefs
    ADD CONSTRAINT livefs__owner__distro_series__name__key UNIQUE (owner, distro_series, name);


ALTER TABLE ONLY public.livefs
    ADD CONSTRAINT livefs_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.livefsfile
    ADD CONSTRAINT livefsfile_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.logintoken
    ADD CONSTRAINT logintoken_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.logintoken
    ADD CONSTRAINT logintoken_token_key UNIQUE (token);


ALTER TABLE ONLY public.lp_account
    ADD CONSTRAINT lp_account__openid_identifier__key UNIQUE (openid_identifier);


ALTER TABLE ONLY public.lp_account
    ADD CONSTRAINT lp_account_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.lp_openididentifier
    ADD CONSTRAINT lp_openididentifier_pkey PRIMARY KEY (identifier);


ALTER TABLE ONLY public.lp_person
    ADD CONSTRAINT lp_person__account__key UNIQUE (account);


ALTER TABLE ONLY public.lp_person
    ADD CONSTRAINT lp_person__name__key UNIQUE (name);


ALTER TABLE ONLY public.lp_person
    ADD CONSTRAINT lp_person_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.lp_personlocation
    ADD CONSTRAINT lp_personlocation__person__key UNIQUE (person);


ALTER TABLE ONLY public.lp_personlocation
    ADD CONSTRAINT lp_personlocation_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.lp_teamparticipation
    ADD CONSTRAINT lp_teamparticipation_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.lp_teamparticipation
    ADD CONSTRAINT lp_teamperticipation__team__person__key UNIQUE (team, person);


ALTER TABLE ONLY public.mailinglist
    ADD CONSTRAINT mailinglist_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.mailinglist
    ADD CONSTRAINT mailinglist_team_key UNIQUE (team);


ALTER TABLE ONLY public.mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT maintainer__upload_archive__upload_distroseries__sourcepackagen UNIQUE (maintainer, upload_archive, upload_distroseries, sourcepackagename);


ALTER TABLE ONLY public.teammembership
    ADD CONSTRAINT membership_person_key UNIQUE (person, team);


ALTER TABLE ONLY public.teammembership
    ADD CONSTRAINT membership_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_pkey PRIMARY KEY (id);

ALTER TABLE public.message CLUSTER ON message_pkey;


ALTER TABLE ONLY public.messageapproval
    ADD CONSTRAINT messageapproval_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.messagechunk
    ADD CONSTRAINT messagechunk_message_idx UNIQUE (message, sequence);


ALTER TABLE ONLY public.messagechunk
    ADD CONSTRAINT messagechunk_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_distribution_id_key UNIQUE (distribution, id);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_name_distribution_key UNIQUE (name, distribution);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_name_product_key UNIQUE (name, product);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_pkey PRIMARY KEY (id);

ALTER TABLE public.milestone CLUSTER ON milestone_pkey;


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_product_id_key UNIQUE (product, id);


ALTER TABLE ONLY public.milestonetag
    ADD CONSTRAINT milestonetag__tag__milestone__key UNIQUE (tag, milestone);


ALTER TABLE ONLY public.milestonetag
    ADD CONSTRAINT milestonetag_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.mirrorcdimagedistroseries
    ADD CONSTRAINT mirrorcdimagedistrorelease_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.mirrorcdimagedistroseries
    ADD CONSTRAINT mirrorcdimagedistroseries__unq UNIQUE (distroseries, flavour, distribution_mirror);


ALTER TABLE ONLY public.mirrordistroarchseries
    ADD CONSTRAINT mirrordistroarchrelease_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.mirrordistroseriessource
    ADD CONSTRAINT mirrordistroreleasesource_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.mirrorproberecord
    ADD CONSTRAINT mirrorproberecord_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.nameblacklist
    ADD CONSTRAINT nameblacklist__regexp__key UNIQUE (regexp);


ALTER TABLE ONLY public.nameblacklist
    ADD CONSTRAINT nameblacklist_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_key_key UNIQUE (key);


ALTER TABLE ONLY public.oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.oauthconsumer
    ADD CONSTRAINT oauthconsumer_key_key UNIQUE (key);


ALTER TABLE ONLY public.oauthconsumer
    ADD CONSTRAINT oauthconsumer_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_key_key UNIQUE (key);


ALTER TABLE ONLY public.oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.officialbugtag
    ADD CONSTRAINT officialbugtag_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.openidconsumerassociation
    ADD CONSTRAINT openidconsumerassociation_pkey PRIMARY KEY (server_url, handle);


ALTER TABLE ONLY public.openidconsumernonce
    ADD CONSTRAINT openidconsumernonce_pkey PRIMARY KEY (server_url, "timestamp", salt);


ALTER TABLE ONLY public.openididentifier
    ADD CONSTRAINT openididentifier_pkey PRIMARY KEY (identifier);


ALTER TABLE ONLY public.packagecopyjob
    ADD CONSTRAINT packagecopyjob__job__key UNIQUE (job);


ALTER TABLE ONLY public.packagecopyjob
    ADD CONSTRAINT packagecopyjob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packagediff
    ADD CONSTRAINT packagediff_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packagesetinclusion
    ADD CONSTRAINT packagepayerinclusion__parent__child__key UNIQUE (parent, child);


ALTER TABLE ONLY public.binarypackagepublishinghistory
    ADD CONSTRAINT packagepublishinghistory_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packageset
    ADD CONSTRAINT packageset__name__distroseries__key UNIQUE (name, distroseries);


ALTER TABLE ONLY public.packageset
    ADD CONSTRAINT packageset_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packagesetgroup
    ADD CONSTRAINT packagesetgroup_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packagesetinclusion
    ADD CONSTRAINT packagesetinclusion_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packagesetsources
    ADD CONSTRAINT packagesetsources__packageset__sourcepackagename__key UNIQUE (packageset, sourcepackagename);


ALTER TABLE ONLY public.packagesetsources
    ADD CONSTRAINT packagesetsources_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packageuploadsource
    ADD CONSTRAINT packageuploadsource__packageupload__key UNIQUE (packageupload);


ALTER TABLE ONLY public.packaging
    ADD CONSTRAINT packaging__distroseries__sourcepackagename__key UNIQUE (distroseries, sourcepackagename);


ALTER TABLE ONLY public.packaging
    ADD CONSTRAINT packaging_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.packagingjob
    ADD CONSTRAINT packagingjob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.parsedapachelog
    ADD CONSTRAINT parsedapachelog_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person__account__key UNIQUE (account);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person__name__key UNIQUE (name);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person_pkey PRIMARY KEY (id);

ALTER TABLE public.person CLUSTER ON person_pkey;


ALTER TABLE ONLY public.personlanguage
    ADD CONSTRAINT personlanguage_person_key UNIQUE (person, language);


ALTER TABLE ONLY public.personlanguage
    ADD CONSTRAINT personlanguage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.personlocation
    ADD CONSTRAINT personlocation_person_key UNIQUE (person);


ALTER TABLE ONLY public.personlocation
    ADD CONSTRAINT personlocation_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.personnotification
    ADD CONSTRAINT personnotification_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.personsettings
    ADD CONSTRAINT personsettings_pkey PRIMARY KEY (person);


ALTER TABLE ONLY public.persontransferjob
    ADD CONSTRAINT persontransferjob_job_key UNIQUE (job);


ALTER TABLE ONLY public.persontransferjob
    ADD CONSTRAINT persontransferjob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.pillarname
    ADD CONSTRAINT pillarname_name_key UNIQUE (name);


ALTER TABLE ONLY public.pillarname
    ADD CONSTRAINT pillarname_pkey PRIMARY KEY (id);

ALTER TABLE public.pillarname CLUSTER ON pillarname_pkey;


ALTER TABLE ONLY public.pocketchroot
    ADD CONSTRAINT pocketchroot__distroarchseries__pocket__image_type__key UNIQUE (distroarchseries, pocket, image_type);


ALTER TABLE ONLY public.pocketchroot
    ADD CONSTRAINT pocketchroot_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.poexportrequest
    ADD CONSTRAINT poexportrequest_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.pofile
    ADD CONSTRAINT pofile_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.pofilestatsjob
    ADD CONSTRAINT pofilestatsjob_pkey PRIMARY KEY (job);


ALTER TABLE ONLY public.pofiletranslator
    ADD CONSTRAINT pofiletranslator__person__pofile__key UNIQUE (person, pofile);

ALTER TABLE public.pofiletranslator CLUSTER ON pofiletranslator__person__pofile__key;


ALTER TABLE ONLY public.pofiletranslator
    ADD CONSTRAINT pofiletranslator_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.poll
    ADD CONSTRAINT poll_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.poll
    ADD CONSTRAINT poll_team_key UNIQUE (team, name);


ALTER TABLE ONLY public.polloption
    ADD CONSTRAINT polloption_name_key UNIQUE (name, poll);


ALTER TABLE ONLY public.polloption
    ADD CONSTRAINT polloption_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.polloption
    ADD CONSTRAINT polloption_poll_key UNIQUE (poll, id);


ALTER TABLE ONLY public.pomsgid
    ADD CONSTRAINT pomsgid_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.potemplate
    ADD CONSTRAINT potemplate_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.potmsgset
    ADD CONSTRAINT potmsgset_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.potranslation
    ADD CONSTRAINT potranslation_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.previewdiff
    ADD CONSTRAINT previewdiff_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.processacceptedbugsjob
    ADD CONSTRAINT processacceptedbugsjob_pkey PRIMARY KEY (job);


ALTER TABLE ONLY public.processor
    ADD CONSTRAINT processor_name_key UNIQUE (name);


ALTER TABLE ONLY public.processor
    ADD CONSTRAINT processor_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_name_key UNIQUE (name);

ALTER TABLE public.product CLUSTER ON product_name_key;


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.productjob
    ADD CONSTRAINT productjob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.productlicense
    ADD CONSTRAINT productlicense__product__license__key UNIQUE (product, license);


ALTER TABLE ONLY public.productlicense
    ADD CONSTRAINT productlicense_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.productrelease
    ADD CONSTRAINT productrelease_milestone_key UNIQUE (milestone);


ALTER TABLE ONLY public.productrelease
    ADD CONSTRAINT productrelease_pkey PRIMARY KEY (id);

ALTER TABLE public.productrelease CLUSTER ON productrelease_pkey;


ALTER TABLE ONLY public.productreleasefile
    ADD CONSTRAINT productreleasefile_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.productseries
    ADD CONSTRAINT productseries__product__name__key UNIQUE (product, name);

ALTER TABLE public.productseries CLUSTER ON productseries__product__name__key;


ALTER TABLE ONLY public.productseries
    ADD CONSTRAINT productseries_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.productseries
    ADD CONSTRAINT productseries_product_series_uniq UNIQUE (product, id);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_name_key UNIQUE (name);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);

ALTER TABLE public.project CLUSTER ON project_pkey;


ALTER TABLE ONLY public.publisherconfig
    ADD CONSTRAINT publisherconfig_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.questionjob
    ADD CONSTRAINT questionjob_job_key UNIQUE (job);


ALTER TABLE ONLY public.questionjob
    ADD CONSTRAINT questionjob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.revision
    ADD CONSTRAINT revision__id__revision_date__key UNIQUE (id, revision_date);


ALTER TABLE ONLY public.revision
    ADD CONSTRAINT revision_revision_id_unique UNIQUE (revision_id);


ALTER TABLE ONLY public.revisioncache
    ADD CONSTRAINT revisioncache_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.branchrevision
    ADD CONSTRAINT revisionnumber_branch_sequence_unique UNIQUE (branch, sequence);


ALTER TABLE ONLY public.branchrevision
    ADD CONSTRAINT revisionnumber_pkey PRIMARY KEY (revision, branch);


ALTER TABLE ONLY public.revisionparent
    ADD CONSTRAINT revisionparent_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.revisionparent
    ADD CONSTRAINT revisionparent_unique UNIQUE (revision, parent_id);


ALTER TABLE ONLY public.revisionproperty
    ADD CONSTRAINT revisionproperty__revision__name__key UNIQUE (revision, name);


ALTER TABLE ONLY public.revisionproperty
    ADD CONSTRAINT revisionproperty_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.scriptactivity
    ADD CONSTRAINT scriptactivity_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.section
    ADD CONSTRAINT section_name_key UNIQUE (name);


ALTER TABLE ONLY public.section
    ADD CONSTRAINT section_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sectionselection
    ADD CONSTRAINT sectionselection_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch__ds__spn__pocket__key UNIQUE (distroseries, sourcepackagename, pocket);


ALTER TABLE ONLY public.seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sharingjob
    ADD CONSTRAINT sharingjob_job_key UNIQUE (job);


ALTER TABLE ONLY public.sharingjob
    ADD CONSTRAINT sharingjob_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.snap
    ADD CONSTRAINT snap__owner__name__key UNIQUE (owner, name);


ALTER TABLE ONLY public.snap
    ADD CONSTRAINT snap_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.snaparch
    ADD CONSTRAINT snaparch_pkey PRIMARY KEY (snap, processor);


ALTER TABLE ONLY public.snapbase
    ADD CONSTRAINT snapbase_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.snapbuildjob
    ADD CONSTRAINT snapbuildjob_pkey PRIMARY KEY (job);


ALTER TABLE ONLY public.snapfile
    ADD CONSTRAINT snapfile_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.snapjob
    ADD CONSTRAINT snapjob_pkey PRIMARY KEY (job);


ALTER TABLE ONLY public.snappydistroseries
    ADD CONSTRAINT snappydistroseries_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.snappyseries
    ADD CONSTRAINT snappyseries_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackageformatselection
    ADD CONSTRAINT sourceformatselection__distroseries__format__key UNIQUE (distroseries, format);


ALTER TABLE ONLY public.sourcepackageformatselection
    ADD CONSTRAINT sourcepackageformatselection_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackagename
    ADD CONSTRAINT sourcepackagename_name_key UNIQUE (name);


ALTER TABLE ONLY public.sourcepackagename
    ADD CONSTRAINT sourcepackagename_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe__owner__name__key UNIQUE (owner, name);


ALTER TABLE ONLY public.sourcepackagerecipedistroseries
    ADD CONSTRAINT sourcepackagerecipe_distroseries_unique UNIQUE (sourcepackagerecipe, distroseries);


ALTER TABLE ONLY public.sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackagerecipedata
    ADD CONSTRAINT sourcepackagerecipedata_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction__name__recipe_data__key UNIQUE (name, recipe_data);


ALTER TABLE ONLY public.sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction__recipe_data__line_number__k UNIQUE (recipe_data, line_number);


ALTER TABLE ONLY public.sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackagerecipedistroseries
    ADD CONSTRAINT sourcepackagerecipedistroseries_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sourcepackagereleasefile
    ADD CONSTRAINT sourcepackagereleasefile_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_distribution_name_uniq UNIQUE (distribution, name);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_product_name_uniq UNIQUE (name, product);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_specurl_uniq UNIQUE (specurl);


ALTER TABLE ONLY public.specificationbranch
    ADD CONSTRAINT specificationbranch__spec_branch_unique UNIQUE (branch, specification);


ALTER TABLE ONLY public.specificationbranch
    ADD CONSTRAINT specificationbranch_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.specificationdependency
    ADD CONSTRAINT specificationdependency_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.specificationdependency
    ADD CONSTRAINT specificationdependency_uniq UNIQUE (specification, dependency);


ALTER TABLE ONLY public.specificationmessage
    ADD CONSTRAINT specificationmessage__specification__message__key UNIQUE (specification, message);


ALTER TABLE ONLY public.specificationmessage
    ADD CONSTRAINT specificationmessage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.specificationsubscription
    ADD CONSTRAINT specificationsubscription_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.specificationsubscription
    ADD CONSTRAINT specificationsubscription_spec_person_uniq UNIQUE (specification, person);


ALTER TABLE ONLY public.specificationworkitem
    ADD CONSTRAINT specificationworkitem_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.spokenin
    ADD CONSTRAINT spokenin__country__language__key UNIQUE (language, country);


ALTER TABLE ONLY public.spokenin
    ADD CONSTRAINT spokenin_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sprint
    ADD CONSTRAINT sprint_name_uniq UNIQUE (name);


ALTER TABLE ONLY public.sprint
    ADD CONSTRAINT sprint_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sprintattendance
    ADD CONSTRAINT sprintattendance_attendance_uniq UNIQUE (attendee, sprint);


ALTER TABLE ONLY public.sprintattendance
    ADD CONSTRAINT sprintattendance_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sprintspecification
    ADD CONSTRAINT sprintspec_uniq UNIQUE (specification, sprint);


ALTER TABLE ONLY public.sprintspecification
    ADD CONSTRAINT sprintspecification_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.sshkey
    ADD CONSTRAINT sshkey_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.suggestivepotemplate
    ADD CONSTRAINT suggestivepotemplate_pkey PRIMARY KEY (potemplate);


ALTER TABLE ONLY public.answercontact
    ADD CONSTRAINT supportcontact__distribution__sourcepackagename__person__key UNIQUE (distribution, sourcepackagename, person);


ALTER TABLE ONLY public.answercontact
    ADD CONSTRAINT supportcontact__product__person__key UNIQUE (product, person);


ALTER TABLE ONLY public.answercontact
    ADD CONSTRAINT supportcontact_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.teamparticipation
    ADD CONSTRAINT teamparticipation_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.teamparticipation
    ADD CONSTRAINT teamparticipation_team_key UNIQUE (team, person);


ALTER TABLE ONLY public.temporaryblobstorage
    ADD CONSTRAINT temporaryblobstorage_file_alias_key UNIQUE (file_alias);


ALTER TABLE ONLY public.temporaryblobstorage
    ADD CONSTRAINT temporaryblobstorage_pkey PRIMARY KEY (id);

ALTER TABLE public.temporaryblobstorage CLUSTER ON temporaryblobstorage_pkey;


ALTER TABLE ONLY public.temporaryblobstorage
    ADD CONSTRAINT temporaryblobstorage_uuid_key UNIQUE (uuid);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT ticket_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.questionmessage
    ADD CONSTRAINT ticketmessage_message_ticket_uniq UNIQUE (message, question);


ALTER TABLE ONLY public.questionmessage
    ADD CONSTRAINT ticketmessage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.questionreopening
    ADD CONSTRAINT ticketreopening_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.questionsubscription
    ADD CONSTRAINT ticketsubscription_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.questionsubscription
    ADD CONSTRAINT ticketsubscription_ticket_person_uniq UNIQUE (question, person);


ALTER TABLE ONLY public.translator
    ADD CONSTRAINT translation_translationgroup_key UNIQUE (translationgroup, language);


ALTER TABLE ONLY public.translationgroup
    ADD CONSTRAINT translationgroup_name_key UNIQUE (name);


ALTER TABLE ONLY public.translationgroup
    ADD CONSTRAINT translationgroup_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.translationrelicensingagreement
    ADD CONSTRAINT translationrelicensingagreement__person__key UNIQUE (person);


ALTER TABLE ONLY public.translationrelicensingagreement
    ADD CONSTRAINT translationrelicensingagreement_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.translationtemplateitem
    ADD CONSTRAINT translationtemplateitem_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.translationtemplatesbuild
    ADD CONSTRAINT translationtemplatesbuild_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.translator
    ADD CONSTRAINT translator_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.usertouseremail
    ADD CONSTRAINT usertouseremail_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.vote
    ADD CONSTRAINT vote_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.votecast
    ADD CONSTRAINT votecast_person_key UNIQUE (person, poll);


ALTER TABLE ONLY public.votecast
    ADD CONSTRAINT votecast_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT webhook_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.webhookjob
    ADD CONSTRAINT webhookjob_pkey PRIMARY KEY (job);


ALTER TABLE ONLY public.wikiname
    ADD CONSTRAINT wikiname_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.wikiname
    ADD CONSTRAINT wikiname_wikiname_key UNIQUE (wikiname, wiki);


ALTER TABLE ONLY public.xref
    ADD CONSTRAINT xref_pkey PRIMARY KEY (from_type, from_id, to_type, to_id);


CREATE UNIQUE INDEX accessartifact__branch__key ON public.accessartifact USING btree (branch) WHERE (branch IS NOT NULL);


CREATE UNIQUE INDEX accessartifact__bug__key ON public.accessartifact USING btree (bug) WHERE (bug IS NOT NULL);


CREATE UNIQUE INDEX accessartifact__gitrepository__key ON public.accessartifact USING btree (gitrepository) WHERE (gitrepository IS NOT NULL);


CREATE UNIQUE INDEX accessartifact__specification__key ON public.accessartifact USING btree (specification) WHERE (specification IS NOT NULL);


CREATE UNIQUE INDEX accessartifactgrant__grantee__artifact__key ON public.accessartifactgrant USING btree (grantee, artifact);


CREATE INDEX accessartifactgrant__grantor__idx ON public.accessartifactgrant USING btree (grantor);


CREATE UNIQUE INDEX accesspolicy__distribution__type__key ON public.accesspolicy USING btree (distribution, type) WHERE (distribution IS NOT NULL);


CREATE UNIQUE INDEX accesspolicy__person__key ON public.accesspolicy USING btree (person) WHERE (person IS NOT NULL);


CREATE UNIQUE INDEX accesspolicy__product__type__key ON public.accesspolicy USING btree (product, type) WHERE (product IS NOT NULL);


CREATE INDEX accesspolicyartifact__policy__key ON public.accesspolicyartifact USING btree (policy);


CREATE UNIQUE INDEX accesspolicygrant__grantee__policy__key ON public.accesspolicygrant USING btree (grantee, policy);


CREATE INDEX accesspolicygrant__grantor__idx ON public.accesspolicygrant USING btree (grantor);


CREATE INDEX accesspolicygrantflat__artifact__grantee__idx ON public.accesspolicygrantflat USING btree (artifact, grantee);


CREATE INDEX accesspolicygrantflat__grantee__policy__idx ON public.accesspolicygrantflat USING btree (grantee, policy);


CREATE UNIQUE INDEX accesspolicygrantflat__policy__grantee__artifact__key ON public.accesspolicygrantflat USING btree (policy, grantee, artifact);


CREATE UNIQUE INDEX accesspolicygrantflat__policy__grantee__key ON public.accesspolicygrantflat USING btree (policy, grantee) WHERE (artifact IS NULL);


CREATE INDEX announcement__distribution__active__idx ON public.announcement USING btree (distribution, active) WHERE (distribution IS NOT NULL);


CREATE INDEX announcement__product__active__idx ON public.announcement USING btree (product, active) WHERE (product IS NOT NULL);


CREATE INDEX announcement__project__active__idx ON public.announcement USING btree (project, active) WHERE (project IS NOT NULL);


CREATE INDEX announcement__registrant__idx ON public.announcement USING btree (registrant);


CREATE UNIQUE INDEX answercontact__distribution__person__key ON public.answercontact USING btree (distribution, person) WHERE (sourcepackagename IS NULL);


CREATE INDEX answercontact__person__idx ON public.answercontact USING btree (person);


CREATE INDEX apportjob__blob__idx ON public.apportjob USING btree (blob);


CREATE UNIQUE INDEX archive__distribution__purpose__distro_archives__key ON public.archive USING btree (distribution, purpose) WHERE (purpose = ANY (ARRAY[1, 4, 7]));


CREATE UNIQUE INDEX archive__distribution__purpose__key ON public.archive USING btree (distribution, purpose) WHERE (purpose = ANY (ARRAY[1, 4]));


CREATE INDEX archive__fti__idx ON public.archive USING gin (fti);


CREATE INDEX archive__owner__idx ON public.archive USING btree (owner);


CREATE UNIQUE INDEX archive__owner__key ON public.archive USING btree (owner, distribution, name);


CREATE INDEX archive__require_virtualized__idx ON public.archive USING btree (require_virtualized);


CREATE INDEX archive__signing_key_fingerprint__idx ON public.archive USING btree (signing_key_fingerprint);


CREATE INDEX archive__signing_key_owner__idx ON public.archive USING btree (signing_key_owner);


CREATE INDEX archive__status__idx ON public.archive USING btree (status);


CREATE INDEX archiveauthtoken__archive__idx ON public.archiveauthtoken USING btree (archive);


CREATE UNIQUE INDEX archiveauthtoken__archive__name__date_deactivated__idx ON public.archiveauthtoken USING btree (archive, name) WHERE ((date_deactivated IS NULL) AND (name IS NOT NULL));


CREATE INDEX archiveauthtoken__date_created__idx ON public.archiveauthtoken USING btree (date_created);


CREATE INDEX archiveauthtoken__person__idx ON public.archiveauthtoken USING btree (person);


CREATE INDEX archivedependency__archive__idx ON public.archivedependency USING btree (archive);


CREATE INDEX archivedependency__dependency__idx ON public.archivedependency USING btree (dependency);


CREATE INDEX archivefile__archive__container__idx ON public.archivefile USING btree (archive, container);


CREATE INDEX archivefile__archive__path__idx ON public.archivefile USING btree (archive, path);


CREATE INDEX archivefile__archive__scheduled_deletion_date__container__idx ON public.archivefile USING btree (archive, scheduled_deletion_date, container) WHERE (scheduled_deletion_date IS NOT NULL);


CREATE INDEX archivefile__library_file__idx ON public.archivefile USING btree (library_file);


CREATE INDEX archivejob__archive__job_type__idx ON public.archivejob USING btree (archive, job_type);


CREATE INDEX archivepermission__archive__component__permission__idx ON public.archivepermission USING btree (archive, component, permission);


CREATE INDEX archivepermission__archive__sourcepackagename__permission__idx ON public.archivepermission USING btree (archive, sourcepackagename, permission);


CREATE INDEX archivepermission__packageset__idx ON public.archivepermission USING btree (packageset) WHERE (packageset IS NOT NULL);


CREATE INDEX archivepermission__person__archive__idx ON public.archivepermission USING btree (person, archive);


CREATE INDEX archivesubscriber__archive__idx ON public.archivesubscriber USING btree (archive);


CREATE INDEX archivesubscriber__cancelled_by__idx ON public.archivesubscriber USING btree (cancelled_by) WHERE (cancelled_by IS NOT NULL);


CREATE INDEX archivesubscriber__date_expires__idx ON public.archivesubscriber USING btree (date_expires) WHERE (date_expires IS NOT NULL);


CREATE INDEX archivesubscriber__registrant__idx ON public.archivesubscriber USING btree (registrant);


CREATE INDEX archivesubscriber__subscriber__idx ON public.archivesubscriber USING btree (subscriber);


CREATE INDEX binarypackagebuild__archive__das__spn__status__finished__idx ON public.binarypackagebuild USING btree (archive, distro_arch_series, source_package_name, status, date_finished, id);


CREATE INDEX binarypackagebuild__archive__status__date_created__id__idx ON public.binarypackagebuild USING btree (archive, status, date_created DESC, id);


CREATE INDEX binarypackagebuild__archive__status__date_finished__id__idx ON public.binarypackagebuild USING btree (archive, status, date_finished DESC, id);


CREATE INDEX binarypackagebuild__build_farm_job__idx ON public.binarypackagebuild USING btree (build_farm_job);


CREATE INDEX binarypackagebuild__builder__status__date_finished__id__idx ON public.binarypackagebuild USING btree (builder, status, date_finished DESC, id) WHERE (builder IS NOT NULL);


CREATE INDEX binarypackagebuild__buildinfo__idx ON public.binarypackagebuild USING btree (buildinfo);


CREATE INDEX binarypackagebuild__das__id__idx ON public.binarypackagebuild USING btree (distro_arch_series, id) WHERE is_distro_archive;


CREATE INDEX binarypackagebuild__das__status__date_finished__id__idx ON public.binarypackagebuild USING btree (distro_arch_series, status, date_finished DESC, id) WHERE is_distro_archive;


CREATE INDEX binarypackagebuild__das__status__id__idx ON public.binarypackagebuild USING btree (distro_arch_series, status, id) WHERE is_distro_archive;


CREATE INDEX binarypackagebuild__distro__id__idx ON public.binarypackagebuild USING btree (distribution, id) WHERE is_distro_archive;


CREATE INDEX binarypackagebuild__distro__status__date_finished__id__idx ON public.binarypackagebuild USING btree (distribution, status, date_finished DESC, id) WHERE is_distro_archive;


CREATE INDEX binarypackagebuild__distro__status__id__idx ON public.binarypackagebuild USING btree (distribution, status, id) WHERE is_distro_archive;


CREATE INDEX binarypackagebuild__ds__id__idx ON public.binarypackagebuild USING btree (distro_series, id) WHERE is_distro_archive;


CREATE INDEX binarypackagebuild__ds__status__date_finished__id__idx ON public.binarypackagebuild USING btree (distro_series, status, date_finished DESC, id) WHERE is_distro_archive;


CREATE INDEX binarypackagebuild__ds__status__id__idx ON public.binarypackagebuild USING btree (distro_series, status, id) WHERE is_distro_archive;


CREATE INDEX binarypackagebuild__log__idx ON public.binarypackagebuild USING btree (log);


CREATE INDEX binarypackagebuild__source_package_name__idx ON public.binarypackagebuild USING btree (source_package_name);


CREATE INDEX binarypackagebuild__spr__archive__status__idx ON public.binarypackagebuild USING btree (source_package_release, archive, status);


CREATE INDEX binarypackagebuild__spr__distro_arch_series__status__idx ON public.binarypackagebuild USING btree (source_package_release, distro_arch_series, status);


CREATE INDEX binarypackagebuild__status__id__idx ON public.binarypackagebuild USING btree (status, id);


CREATE INDEX binarypackagebuild__upload_log__idx ON public.binarypackagebuild USING btree (upload_log);


CREATE INDEX binarypackagefile_binarypackage_idx ON public.binarypackagefile USING btree (binarypackagerelease);


CREATE INDEX binarypackagefile_libraryfile_idx ON public.binarypackagefile USING btree (libraryfile);


CREATE INDEX binarypackagename__name__trgm ON public.binarypackagename USING gin (name trgm.gin_trgm_ops);


CREATE INDEX binarypackagepublishinghistory__archive__bpn__status__idx ON public.binarypackagepublishinghistory USING btree (archive, binarypackagename, status);


CREATE INDEX binarypackagepublishinghistory__archive__bpr__status__idx ON public.binarypackagepublishinghistory USING btree (archive, binarypackagerelease, status);


CREATE INDEX binarypackagepublishinghistory__archive__das__bpn__idx ON public.binarypackagepublishinghistory USING btree (archive, distroarchseries, binarypackagename);


CREATE INDEX binarypackagepublishinghistory__archive__datecreated__id__idx ON public.binarypackagepublishinghistory USING btree (archive, datecreated, id);


CREATE INDEX binarypackagepublishinghistory__archive__distroarchseries__stat ON public.binarypackagepublishinghistory USING btree (archive, distroarchseries, status, binarypackagename);


CREATE INDEX binarypackagepublishinghistory__archive__status__scheduleddelet ON public.binarypackagepublishinghistory USING btree (archive, status) WHERE (scheduleddeletiondate IS NULL);


CREATE INDEX binarypackagepublishinghistory__binarypackagename__idx ON public.binarypackagepublishinghistory USING btree (binarypackagename);


CREATE INDEX binarypackagepublishinghistory__supersededby__idx ON public.binarypackagepublishinghistory USING btree (supersededby);


CREATE INDEX binarypackagerelease__binarypackagename__version__idx ON public.binarypackagerelease USING btree (binarypackagename, version);


CREATE UNIQUE INDEX binarypackagerelease__debug_package__key ON public.binarypackagerelease USING btree (debug_package);


CREATE INDEX binarypackagerelease_build_idx ON public.binarypackagerelease USING btree (build);


CREATE INDEX binarypackagereleasedownloadcount__binary_package_release__idx ON public.binarypackagereleasedownloadcount USING btree (binary_package_release);


CREATE UNIQUE INDEX branch__ds__spn__owner__name__key ON public.branch USING btree (distroseries, sourcepackagename, owner, name) WHERE (distroseries IS NOT NULL);


CREATE INDEX branch__information_type__idx ON public.branch USING btree (information_type);


CREATE INDEX branch__last_scanned__owner__idx ON public.branch USING btree (last_scanned, owner) WHERE (last_scanned IS NOT NULL);


CREATE INDEX branch__name__trgm ON public.branch USING gin (lower(name) trgm.gin_trgm_ops);


CREATE INDEX branch__next_mirror_time__idx ON public.branch USING btree (next_mirror_time) WHERE (next_mirror_time IS NOT NULL);


CREATE UNIQUE INDEX branch__owner__name__key ON public.branch USING btree (owner, name) WHERE ((product IS NULL) AND (distroseries IS NULL));


CREATE INDEX branch__product__id__idx ON public.branch USING btree (product, id);

ALTER TABLE public.branch CLUSTER ON branch__product__id__idx;


CREATE UNIQUE INDEX branch__product__owner__name__key ON public.branch USING btree (product, owner, name) WHERE (product IS NOT NULL);


CREATE INDEX branch__registrant__idx ON public.branch USING btree (registrant);


CREATE INDEX branch__reviewer__idx ON public.branch USING btree (reviewer);


CREATE INDEX branch__stacked_on__idx ON public.branch USING btree (stacked_on) WHERE (stacked_on IS NOT NULL);


CREATE INDEX branch__unique_name__trgm ON public.branch USING gin (lower(unique_name) trgm.gin_trgm_ops);


CREATE INDEX branch_owner_idx ON public.branch USING btree (owner);


CREATE INDEX branchjob__branch__idx ON public.branchjob USING btree (branch);


CREATE INDEX branchmergeproposal__dependent_branch__idx ON public.branchmergeproposal USING btree (dependent_branch);


CREATE INDEX branchmergeproposal__merge_log_file__idx ON public.branchmergeproposal USING btree (merge_log_file);


CREATE INDEX branchmergeproposal__merge_reporter__idx ON public.branchmergeproposal USING btree (merge_reporter) WHERE (merge_reporter IS NOT NULL);


CREATE INDEX branchmergeproposal__merger__idx ON public.branchmergeproposal USING btree (merger);


CREATE INDEX branchmergeproposal__queuer__idx ON public.branchmergeproposal USING btree (queuer);


CREATE INDEX branchmergeproposal__registrant__idx ON public.branchmergeproposal USING btree (registrant);


CREATE INDEX branchmergeproposal__reviewer__idx ON public.branchmergeproposal USING btree (reviewer);


CREATE INDEX branchmergeproposal__source_branch__idx ON public.branchmergeproposal USING btree (source_branch);


CREATE INDEX branchmergeproposal__superseded_by__idx ON public.branchmergeproposal USING btree (superseded_by) WHERE (superseded_by IS NOT NULL);


CREATE INDEX branchmergeproposal__target_branch__idx ON public.branchmergeproposal USING btree (target_branch);


CREATE INDEX branchmergeproposaljob__branch_merge_proposal__idx ON public.branchmergeproposaljob USING btree (branch_merge_proposal);


CREATE INDEX branchsubscription__branch__idx ON public.branchsubscription USING btree (branch);


CREATE INDEX branchsubscription__subscribed_by__idx ON public.branchsubscription USING btree (subscribed_by);


CREATE INDEX bug__date_last_message__idx ON public.bug USING btree (date_last_message);


CREATE INDEX bug__date_last_updated__idx ON public.bug USING btree (date_last_updated);

ALTER TABLE public.bug CLUSTER ON bug__date_last_updated__idx;


CREATE INDEX bug__datecreated__idx ON public.bug USING btree (datecreated);


CREATE INDEX bug__heat__idx ON public.bug USING btree (heat);


CREATE INDEX bug__heat_last_updated__idx ON public.bug USING btree (heat_last_updated);


CREATE INDEX bug__information_type__idx ON public.bug USING btree (information_type);


CREATE INDEX bug__latest_patch_uploaded__idx ON public.bug USING btree (latest_patch_uploaded);


CREATE UNIQUE INDEX bug__name__key ON public.bug USING btree (name) WHERE (name IS NOT NULL);


CREATE INDEX bug__new_patches__idx ON public.bug USING btree (id) WHERE ((latest_patch_uploaded IS NOT NULL) AND (duplicateof IS NULL));


CREATE INDEX bug__users_affected_count__idx ON public.bug USING btree (users_affected_count);


CREATE INDEX bug__users_unaffected_count__idx ON public.bug USING btree (users_unaffected_count);


CREATE INDEX bug__who_made_private__idx ON public.bug USING btree (who_made_private) WHERE (who_made_private IS NOT NULL);


CREATE INDEX bug_duplicateof_idx ON public.bug USING btree (duplicateof);


CREATE INDEX bug_owner_idx ON public.bug USING btree (owner);


CREATE INDEX bugactivity_bug_datechanged_idx ON public.bugactivity USING btree (bug, datechanged);


CREATE INDEX bugactivity_datechanged_idx ON public.bugactivity USING btree (datechanged);


CREATE INDEX bugactivity_person_datechanged_idx ON public.bugactivity USING btree (person, datechanged);


CREATE INDEX bugaffectsperson__person__idx ON public.bugaffectsperson USING btree (person);


CREATE INDEX bugattachment__bug__idx ON public.bugattachment USING btree (bug);


CREATE INDEX bugattachment_libraryfile_idx ON public.bugattachment USING btree (libraryfile);


CREATE INDEX bugattachment_message_idx ON public.bugattachment USING btree (message);


CREATE INDEX bugbranch__branch__idx ON public.bugbranch USING btree (branch);


CREATE INDEX bugbranch__registrant__idx ON public.bugbranch USING btree (registrant);


CREATE INDEX bugmessage__owner__index__idx ON public.bugmessage USING btree (owner, index);


CREATE INDEX bugmessage_message_idx ON public.bugmessage USING btree (message);


CREATE INDEX bugmute__bug__idx ON public.bugmute USING btree (bug);


CREATE INDEX bugnomination__bug__idx ON public.bugnomination USING btree (bug);


CREATE INDEX bugnomination__decider__idx ON public.bugnomination USING btree (decider) WHERE (decider IS NOT NULL);


CREATE UNIQUE INDEX bugnomination__distroseries__bug__key ON public.bugnomination USING btree (distroseries, bug) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugnomination__owner__idx ON public.bugnomination USING btree (owner);


CREATE UNIQUE INDEX bugnomination__productseries__bug__key ON public.bugnomination USING btree (productseries, bug) WHERE (productseries IS NOT NULL);


CREATE INDEX bugnotification__date_emailed__idx ON public.bugnotification USING btree (date_emailed);

ALTER TABLE public.bugnotification CLUSTER ON bugnotification__date_emailed__idx;


CREATE INDEX bugnotificationattachment__bug_notification__idx ON public.bugnotificationattachment USING btree (bug_notification);


CREATE INDEX bugnotificationattachment__message__idx ON public.bugnotificationattachment USING btree (message);


CREATE INDEX bugnotificationfilter__bug_subscription_filter__idx ON public.bugnotificationfilter USING btree (bug_subscription_filter);


CREATE INDEX bugnotificationrecipient__person__idx ON public.bugnotificationrecipient USING btree (person);


CREATE INDEX bugsubscription__subscribed_by__idx ON public.bugsubscription USING btree (subscribed_by);


CREATE INDEX bugsubscription_bug_idx ON public.bugsubscription USING btree (bug);

ALTER TABLE public.bugsubscription CLUSTER ON bugsubscription_bug_idx;


CREATE INDEX bugsubscription_person_idx ON public.bugsubscription USING btree (person);


CREATE INDEX bugsubscriptionfilter__bug_notification_level__idx ON public.bugsubscriptionfilter USING btree (bug_notification_level);


CREATE INDEX bugsubscriptionfilter__structuralsubscription ON public.bugsubscriptionfilter USING btree (structuralsubscription);


CREATE INDEX bugsubscriptionfiltermute__filter__idx ON public.bugsubscriptionfiltermute USING btree (filter);


CREATE INDEX bugsubscriptionfiltertag__filter__tag__idx ON public.bugsubscriptionfiltertag USING btree (filter, tag);


CREATE INDEX bugsummary__distribution__idx ON public.bugsummary USING btree (distribution, sourcepackagename) WHERE (distribution IS NOT NULL);


CREATE INDEX bugsummary__distribution_count__idx ON public.bugsummary USING btree (distribution, sourcepackagename, status) WHERE ((distribution IS NOT NULL) AND (tag IS NULL));


CREATE INDEX bugsummary__distribution_tag_count__idx ON public.bugsummary USING btree (distribution, sourcepackagename, status) WHERE ((distribution IS NOT NULL) AND (tag IS NOT NULL));


CREATE INDEX bugsummary__distroseries__idx ON public.bugsummary USING btree (distroseries, sourcepackagename) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugsummary__distroseries_count__idx ON public.bugsummary USING btree (distroseries, sourcepackagename, status) WHERE ((distroseries IS NOT NULL) AND (tag IS NULL));


CREATE INDEX bugsummary__distroseries_tag_count__idx ON public.bugsummary USING btree (distroseries, sourcepackagename, status) WHERE ((distroseries IS NOT NULL) AND (tag IS NOT NULL));


CREATE INDEX bugsummary__full__idx ON public.bugsummary USING btree (tag, status, product, productseries, distribution, distroseries, sourcepackagename, viewed_by, access_policy, milestone, importance);


CREATE INDEX bugsummary__milestone__idx ON public.bugsummary USING btree (milestone) WHERE (milestone IS NOT NULL);


CREATE INDEX bugsummary__nocount__idx ON public.bugsummary USING btree (count) WHERE (count = 0);


CREATE INDEX bugsummary__product__idx ON public.bugsummary USING btree (product) WHERE (product IS NOT NULL);


CREATE INDEX bugsummary__productseries__idx ON public.bugsummary USING btree (productseries) WHERE (productseries IS NOT NULL);


CREATE INDEX bugsummary__status_count__idx ON public.bugsummary USING btree (status) WHERE ((sourcepackagename IS NULL) AND (tag IS NULL));


CREATE UNIQUE INDEX bugsummary__unique ON public.bugsummary USING btree ((COALESCE(product, (-1))), (COALESCE(productseries, (-1))), (COALESCE(distribution, (-1))), (COALESCE(distroseries, (-1))), (COALESCE(sourcepackagename, (-1))), status, importance, has_patch, (COALESCE(tag, ''::text)), (COALESCE(milestone, (-1))), (COALESCE(viewed_by, (-1))), (COALESCE(access_policy, (-1))));


CREATE INDEX bugsummary__viewed_by__idx ON public.bugsummary USING btree (viewed_by) WHERE (viewed_by IS NOT NULL);


CREATE INDEX bugsummaryjournal__full__idx ON public.bugsummaryjournal USING btree (status, product, productseries, distribution, distroseries, sourcepackagename, viewed_by, milestone, tag);


CREATE INDEX bugsummaryjournal__milestone__idx ON public.bugsummaryjournal USING btree (milestone) WHERE (milestone IS NOT NULL);


CREATE INDEX bugsummaryjournal__viewed_by__idx ON public.bugsummaryjournal USING btree (viewed_by) WHERE (viewed_by IS NOT NULL);


CREATE INDEX bugtag__bug__idx ON public.bugtag USING btree (bug);


CREATE INDEX bugtask__assignee__idx ON public.bugtask USING btree (assignee);


CREATE INDEX bugtask__bug__idx ON public.bugtask USING btree (bug);


CREATE INDEX bugtask__bugwatch__idx ON public.bugtask USING btree (bugwatch) WHERE (bugwatch IS NOT NULL);


CREATE INDEX bugtask__date_closed__id__idx2 ON public.bugtask USING btree (date_closed, id DESC);


CREATE INDEX bugtask__date_incomplete__idx ON public.bugtask USING btree (date_incomplete) WHERE (date_incomplete IS NOT NULL);


CREATE INDEX bugtask__datecreated__idx ON public.bugtask USING btree (datecreated);


CREATE INDEX bugtask__distribution__sourcepackagename__idx ON public.bugtask USING btree (distribution, sourcepackagename);

ALTER TABLE public.bugtask CLUSTER ON bugtask__distribution__sourcepackagename__idx;


CREATE INDEX bugtask__distroseries__sourcepackagename__idx ON public.bugtask USING btree (distroseries, sourcepackagename);


CREATE INDEX bugtask__milestone__idx ON public.bugtask USING btree (milestone);


CREATE INDEX bugtask__owner__idx ON public.bugtask USING btree (owner);


CREATE UNIQUE INDEX bugtask__product__bug__key ON public.bugtask USING btree (product, bug) WHERE (product IS NOT NULL);


CREATE UNIQUE INDEX bugtask__productseries__bug__key ON public.bugtask USING btree (productseries, bug) WHERE (productseries IS NOT NULL);


CREATE INDEX bugtask__sourcepackagename__idx ON public.bugtask USING btree (sourcepackagename) WHERE (sourcepackagename IS NOT NULL);


CREATE INDEX bugtask__status__idx ON public.bugtask USING btree (status);


CREATE UNIQUE INDEX bugtask_distinct_sourcepackage_assignment ON public.bugtask USING btree (bug, (COALESCE(sourcepackagename, (-1))), (COALESCE(distroseries, (-1))), (COALESCE(distribution, (-1)))) WHERE ((product IS NULL) AND (productseries IS NULL));


CREATE INDEX bugtask_importance_idx ON public.bugtask USING btree (importance, id DESC);


CREATE INDEX bugtaskflat__assignee__idx ON public.bugtaskflat USING btree (assignee);


CREATE INDEX bugtaskflat__bug__bugtask__idx ON public.bugtaskflat USING btree (bug, bugtask DESC);


CREATE INDEX bugtaskflat__bug__idx ON public.bugtaskflat USING btree (bug);


CREATE INDEX bugtaskflat__bug_owner__idx ON public.bugtaskflat USING btree (bug_owner);


CREATE INDEX bugtaskflat__date_closed__bugtask__idx ON public.bugtaskflat USING btree (date_closed, bugtask DESC);


CREATE INDEX bugtaskflat__date_last_updated__idx ON public.bugtaskflat USING btree (date_last_updated);


CREATE INDEX bugtaskflat__datecreated__idx ON public.bugtaskflat USING btree (datecreated);


CREATE INDEX bugtaskflat__distribution__bug__bugtask__idx ON public.bugtaskflat USING btree (distribution, bug, bugtask DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__date_closed__bugtask__idx ON public.bugtaskflat USING btree (distribution, date_closed, bugtask DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__date_last_updated__idx ON public.bugtaskflat USING btree (distribution, date_last_updated) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__datecreated__idx ON public.bugtaskflat USING btree (distribution, datecreated) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__heat__bugtask__idx ON public.bugtaskflat USING btree (distribution, heat, bugtask DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__importance__bugtask__idx ON public.bugtaskflat USING btree (distribution, importance, bugtask DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__latest_patch_uploaded__bugtask__idx ON public.bugtaskflat USING btree (distribution, latest_patch_uploaded, bugtask DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__spn__bug__idx ON public.bugtaskflat USING btree (distribution, sourcepackagename, bug) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__spn__date_closed__bug__idx ON public.bugtaskflat USING btree (distribution, sourcepackagename, date_closed, bug DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__spn__date_last_updated__idx ON public.bugtaskflat USING btree (distribution, sourcepackagename, date_last_updated) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__spn__datecreated__idx ON public.bugtaskflat USING btree (distribution, sourcepackagename, datecreated) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__spn__heat__bug__idx ON public.bugtaskflat USING btree (distribution, sourcepackagename, heat, bug DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__spn__importance__bug__idx ON public.bugtaskflat USING btree (distribution, sourcepackagename, importance, bug DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__spn__latest_patch_uploaded__bug__idx ON public.bugtaskflat USING btree (distribution, sourcepackagename, latest_patch_uploaded, bug DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__spn__status__bug__idx ON public.bugtaskflat USING btree (distribution, sourcepackagename, status, bug DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distribution__status__bugtask__idx ON public.bugtaskflat USING btree (distribution, status, bugtask DESC) WHERE (distribution IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__bug__bugtask__idx ON public.bugtaskflat USING btree (distroseries, bug, bugtask DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__date_closed__bugtask__idx ON public.bugtaskflat USING btree (distroseries, date_closed, bugtask DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__date_last_updated__idx ON public.bugtaskflat USING btree (distroseries, date_last_updated) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__datecreated__idx ON public.bugtaskflat USING btree (distroseries, datecreated) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__heat__bugtask__idx ON public.bugtaskflat USING btree (distroseries, heat, bugtask DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__importance__bugtask__idx ON public.bugtaskflat USING btree (distroseries, importance, bugtask DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__latest_patch_uploaded__bugtask__idx ON public.bugtaskflat USING btree (distroseries, latest_patch_uploaded, bugtask DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__spn__bug__idx ON public.bugtaskflat USING btree (distroseries, sourcepackagename, bug) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__spn__date_closed__bug__idx ON public.bugtaskflat USING btree (distroseries, sourcepackagename, date_closed, bug DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__spn__date_last_updated__idx ON public.bugtaskflat USING btree (distroseries, sourcepackagename, date_last_updated) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__spn__datecreated__idx ON public.bugtaskflat USING btree (distroseries, sourcepackagename, datecreated) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__spn__heat__bug__idx ON public.bugtaskflat USING btree (distroseries, sourcepackagename, heat, bug DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__spn__importance__bug__idx ON public.bugtaskflat USING btree (distroseries, sourcepackagename, importance, bug DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__spn__latest_patch_uploaded__bug__idx ON public.bugtaskflat USING btree (distroseries, sourcepackagename, latest_patch_uploaded, bug DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__spn__status__bug__idx ON public.bugtaskflat USING btree (distroseries, sourcepackagename, status, bug DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__distroseries__status__bugtask__idx ON public.bugtaskflat USING btree (distroseries, status, bugtask DESC) WHERE (distroseries IS NOT NULL);


CREATE INDEX bugtaskflat__fti__idx ON public.bugtaskflat USING gin (fti);


CREATE INDEX bugtaskflat__heat__bugtask__idx ON public.bugtaskflat USING btree (heat, bugtask DESC);


CREATE INDEX bugtaskflat__importance__bugtask__idx ON public.bugtaskflat USING btree (importance, bugtask DESC);


CREATE INDEX bugtaskflat__latest_patch_uploaded__bugtask__idx ON public.bugtaskflat USING btree (latest_patch_uploaded, bugtask DESC);


CREATE INDEX bugtaskflat__milestone__idx ON public.bugtaskflat USING btree (milestone);


CREATE INDEX bugtaskflat__owner__idx ON public.bugtaskflat USING btree (owner);


CREATE INDEX bugtaskflat__product__bug__idx ON public.bugtaskflat USING btree (product, bug) WHERE (product IS NOT NULL);


CREATE INDEX bugtaskflat__product__date_closed__bug__idx ON public.bugtaskflat USING btree (product, date_closed, bug DESC) WHERE (product IS NOT NULL);


CREATE INDEX bugtaskflat__product__date_last_updated__idx ON public.bugtaskflat USING btree (product, date_last_updated) WHERE (product IS NOT NULL);


CREATE INDEX bugtaskflat__product__datecreated__idx ON public.bugtaskflat USING btree (product, datecreated) WHERE (product IS NOT NULL);


CREATE INDEX bugtaskflat__product__heat__bug__idx ON public.bugtaskflat USING btree (product, heat, bug DESC) WHERE (product IS NOT NULL);


CREATE INDEX bugtaskflat__product__importance__bug__idx ON public.bugtaskflat USING btree (product, importance, bug DESC) WHERE (product IS NOT NULL);


CREATE INDEX bugtaskflat__product__latest_patch_uploaded__bug__idx ON public.bugtaskflat USING btree (product, latest_patch_uploaded, bug DESC) WHERE (product IS NOT NULL);


CREATE INDEX bugtaskflat__product__status__bug__idx ON public.bugtaskflat USING btree (product, status, bug DESC) WHERE (product IS NOT NULL);


CREATE INDEX bugtaskflat__productseries__bug__idx ON public.bugtaskflat USING btree (productseries, bug) WHERE (productseries IS NOT NULL);


CREATE INDEX bugtaskflat__productseries__date_closed__bug__idx ON public.bugtaskflat USING btree (productseries, date_closed, bug DESC) WHERE (productseries IS NOT NULL);


CREATE INDEX bugtaskflat__productseries__date_last_updated__idx ON public.bugtaskflat USING btree (productseries, date_last_updated) WHERE (productseries IS NOT NULL);


CREATE INDEX bugtaskflat__productseries__datecreated__idx ON public.bugtaskflat USING btree (productseries, datecreated) WHERE (productseries IS NOT NULL);


CREATE INDEX bugtaskflat__productseries__heat__bug__idx ON public.bugtaskflat USING btree (productseries, heat, bug DESC) WHERE (productseries IS NOT NULL);


CREATE INDEX bugtaskflat__productseries__importance__bug__idx ON public.bugtaskflat USING btree (productseries, importance, bug DESC) WHERE (productseries IS NOT NULL);


CREATE INDEX bugtaskflat__productseries__latest_patch_uploaded__bug__idx ON public.bugtaskflat USING btree (productseries, latest_patch_uploaded, bug DESC) WHERE (productseries IS NOT NULL);


CREATE INDEX bugtaskflat__productseries__status__bug__idx ON public.bugtaskflat USING btree (productseries, status, bug DESC) WHERE (productseries IS NOT NULL);


CREATE INDEX bugtaskflat__status__bugtask__idx ON public.bugtaskflat USING btree (status, bugtask DESC);


CREATE UNIQUE INDEX bugtracker_name_key ON public.bugtracker USING btree (name);


CREATE INDEX bugtracker_owner_idx ON public.bugtracker USING btree (owner);


CREATE INDEX bugtrackeralias__bugtracker__idx ON public.bugtrackeralias USING btree (bugtracker);


CREATE INDEX bugtrackerperson__person__idx ON public.bugtrackerperson USING btree (person);


CREATE INDEX bugwatch__lastchecked__idx ON public.bugwatch USING btree (lastchecked);


CREATE INDEX bugwatch__next_check__idx ON public.bugwatch USING btree (next_check);


CREATE INDEX bugwatch__remote_lp_bug_id__idx ON public.bugwatch USING btree (remote_lp_bug_id) WHERE (remote_lp_bug_id IS NOT NULL);


CREATE INDEX bugwatch__remotebug__idx ON public.bugwatch USING btree (remotebug);


CREATE INDEX bugwatch_bug_idx ON public.bugwatch USING btree (bug);


CREATE INDEX bugwatch_bugtracker_idx ON public.bugwatch USING btree (bugtracker);


CREATE INDEX bugwatch_datecreated_idx ON public.bugwatch USING btree (datecreated);


CREATE INDEX bugwatch_owner_idx ON public.bugwatch USING btree (owner);


CREATE INDEX bugwatchactivity__bug_watch__idx ON public.bugwatchactivity USING btree (bug_watch);

ALTER TABLE public.bugwatchactivity CLUSTER ON bugwatchactivity__bug_watch__idx;


CREATE INDEX builder__owner__idx ON public.builder USING btree (owner);


CREATE INDEX builderprocessor__processor__idx ON public.builderprocessor USING btree (processor);


CREATE INDEX buildfarmjob__archive__date_created__id__idx ON public.buildfarmjob USING btree (archive, date_created DESC, id) WHERE (archive IS NOT NULL);


CREATE INDEX buildfarmjob__archive__status__date_created__id__idx ON public.buildfarmjob USING btree (archive, status, date_created DESC, id) WHERE (archive IS NOT NULL);


CREATE INDEX buildfarmjob__archive__status__date_finished__id__idx ON public.buildfarmjob USING btree (archive, status, date_finished DESC, id) WHERE (archive IS NOT NULL);


CREATE INDEX buildfarmjob__builder__date_finished__id__idx ON public.buildfarmjob USING btree (builder, date_finished DESC, id) WHERE (builder IS NOT NULL);


CREATE INDEX buildfarmjob__builder__status__date_finished__id__idx ON public.buildfarmjob USING btree (builder, status, date_finished DESC, id) WHERE (builder IS NOT NULL);


CREATE UNIQUE INDEX buildqueue__build_farm_job__key ON public.buildqueue USING btree (build_farm_job);


CREATE UNIQUE INDEX buildqueue__builder__id__idx ON public.buildqueue USING btree (builder, id);

ALTER TABLE public.buildqueue CLUSTER ON buildqueue__builder__id__idx;


CREATE UNIQUE INDEX buildqueue__builder__unq ON public.buildqueue USING btree (builder) WHERE (builder IS NOT NULL);


CREATE INDEX buildqueue__status__lastscore__id__idx ON public.buildqueue USING btree (status, lastscore DESC, id);


CREATE INDEX buildqueue__status__virtualized__processor__lastscore__id__idx ON public.buildqueue USING btree (status, virtualized, processor, lastscore DESC, id);


CREATE INDEX codeimport__assignee__idx ON public.codeimport USING btree (assignee);


CREATE UNIQUE INDEX codeimport__branch__key ON public.codeimport USING btree (branch) WHERE (branch IS NOT NULL);


CREATE UNIQUE INDEX codeimport__cvs_root__cvs_module__key ON public.codeimport USING btree (cvs_root, cvs_module) WHERE (cvs_root IS NOT NULL);


CREATE UNIQUE INDEX codeimport__git_repository__key ON public.codeimport USING btree (git_repository) WHERE (git_repository IS NOT NULL);


CREATE INDEX codeimport__owner__idx ON public.codeimport USING btree (owner);


CREATE INDEX codeimport__registrant__idx ON public.codeimport USING btree (registrant);


CREATE UNIQUE INDEX codeimport__url__branch__idx ON public.codeimport USING btree (url) WHERE ((url IS NOT NULL) AND (branch IS NOT NULL));


CREATE UNIQUE INDEX codeimport__url__git_repository__idx ON public.codeimport USING btree (url) WHERE ((url IS NOT NULL) AND (git_repository IS NOT NULL));


CREATE INDEX codeimportevent__code_import__date_created__id__idx ON public.codeimportevent USING btree (code_import, date_created, id);


CREATE INDEX codeimportevent__date_created__id__idx ON public.codeimportevent USING btree (date_created, id);


CREATE INDEX codeimportevent__message__date_created__idx ON public.codeimportevent USING btree (machine, date_created) WHERE (machine IS NOT NULL);


CREATE INDEX codeimportevent__person__idx ON public.codeimportevent USING btree (person) WHERE (person IS NOT NULL);


CREATE INDEX codeimportjob__machine__date_created__idx ON public.codeimportjob USING btree (machine, date_created);


CREATE INDEX codeimportjob__requesting_user__idx ON public.codeimportjob USING btree (requesting_user);


CREATE INDEX codeimportresult__code_import__date_created__idx ON public.codeimportresult USING btree (code_import, date_created);


CREATE INDEX codeimportresult__log_file__idx ON public.codeimportresult USING btree (log_file);


CREATE INDEX codeimportresult__requesting_user__idx ON public.codeimportresult USING btree (requesting_user);


CREATE INDEX codereviewinlinecomment__person__idx ON public.codereviewinlinecomment USING btree (person);


CREATE INDEX codereviewinlinecomment__previewdiff__idx ON public.codereviewinlinecomment USING btree (previewdiff);


CREATE INDEX codereviewinlinecommentdraft__person__idx ON public.codereviewinlinecommentdraft USING btree (person);


CREATE INDEX codereviewvote__branch_merge_proposal__idx ON public.codereviewvote USING btree (branch_merge_proposal);


CREATE INDEX codereviewvote__registrant__idx ON public.codereviewvote USING btree (registrant);


CREATE INDEX codereviewvote__reviewer__idx ON public.codereviewvote USING btree (reviewer);


CREATE INDEX codereviewvote__vote_message__idx ON public.codereviewvote USING btree (vote_message);


CREATE INDEX commercialsubscription__product__idx ON public.commercialsubscription USING btree (product);


CREATE INDEX commercialsubscription__purchaser__idx ON public.commercialsubscription USING btree (purchaser);


CREATE INDEX commercialsubscription__registrant__idx ON public.commercialsubscription USING btree (registrant);


CREATE INDEX commercialsubscription__sales_system_id__idx ON public.commercialsubscription USING btree (sales_system_id);


CREATE UNIQUE INDEX customlanguagecode__distribution__sourcepackagename__code__key ON public.customlanguagecode USING btree (distribution, sourcepackagename, language_code) WHERE (distribution IS NOT NULL);


CREATE UNIQUE INDEX customlanguagecode__product__code__key ON public.customlanguagecode USING btree (product, language_code) WHERE (product IS NOT NULL);


CREATE INDEX cve__fti__idx ON public.cve USING gin (fti);


CREATE INDEX cve_datemodified_idx ON public.cve USING btree (datemodified);


CREATE INDEX cvereference_cve_idx ON public.cvereference USING btree (cve);


CREATE INDEX diff__diff_text__idx ON public.diff USING btree (diff_text);


CREATE INDEX distribution__bug_supervisor__idx ON public.distribution USING btree (bug_supervisor) WHERE (bug_supervisor IS NOT NULL);


CREATE INDEX distribution__driver__idx ON public.distribution USING btree (driver);


CREATE INDEX distribution__fti__idx ON public.distribution USING gin (fti);


CREATE INDEX distribution__icon__idx ON public.distribution USING btree (icon) WHERE (icon IS NOT NULL);


CREATE INDEX distribution__language_pack_admin__idx ON public.distribution USING btree (language_pack_admin);


CREATE INDEX distribution__logo__idx ON public.distribution USING btree (logo) WHERE (logo IS NOT NULL);


CREATE INDEX distribution__members__idx ON public.distribution USING btree (members);


CREATE INDEX distribution__mirror_admin__idx ON public.distribution USING btree (mirror_admin);


CREATE INDEX distribution__mugshot__idx ON public.distribution USING btree (mugshot) WHERE (mugshot IS NOT NULL);


CREATE INDEX distribution__owner__idx ON public.distribution USING btree (owner);


CREATE INDEX distribution__registrant__idx ON public.distribution USING btree (registrant);


CREATE UNIQUE INDEX distribution_job__initialize_series__distroseries ON public.distributionjob USING btree (distroseries) WHERE (job_type = 1);


CREATE INDEX distribution_translationgroup_idx ON public.distribution USING btree (translationgroup);


CREATE UNIQUE INDEX distributionmirror__archive__distribution__country__key ON public.distributionmirror USING btree (distribution, country, content) WHERE ((country_dns_mirror IS TRUE) AND (content = 1));


CREATE INDEX distributionmirror__country__status__idx ON public.distributionmirror USING btree (country, status);


CREATE INDEX distributionmirror__owner__idx ON public.distributionmirror USING btree (owner);


CREATE UNIQUE INDEX distributionmirror__releases__distribution__country__key ON public.distributionmirror USING btree (distribution, country, content) WHERE ((country_dns_mirror IS TRUE) AND (content = 2));


CREATE INDEX distributionmirror__reviewer__idx ON public.distributionmirror USING btree (reviewer);


CREATE INDEX distributionmirror__status__idx ON public.distributionmirror USING btree (status);


CREATE INDEX distributionsourcepackagecache__archive__idx ON public.distributionsourcepackagecache USING btree (archive);


CREATE INDEX distributionsourcepackagecache__binpkgnames__idx ON public.distributionsourcepackagecache USING gin (binpkgnames trgm.gin_trgm_ops);


CREATE INDEX distributionsourcepackagecache__fti__idx ON public.distributionsourcepackagecache USING gin (fti);


CREATE INDEX distributionsourcepackagecache__name__idx ON public.distributionsourcepackagecache USING gin (name trgm.gin_trgm_ops);


CREATE INDEX distributionsourcepackagecache__sourcepackagename__archive__idx ON public.distributionsourcepackagecache USING btree (sourcepackagename, archive);


CREATE INDEX distroarchseries__distroseries__idx ON public.distroarchseries USING btree (distroseries);


CREATE INDEX distroarchseries__owner__idx ON public.distroarchseries USING btree (owner);


CREATE INDEX distroseries__driver__idx ON public.distroseries USING btree (driver) WHERE (driver IS NOT NULL);


CREATE INDEX distroseries__registrant__idx ON public.distroseries USING btree (registrant);


CREATE INDEX distroseriesdifference__base_version__idx ON public.distroseriesdifference USING btree (base_version);


CREATE INDEX distroseriesdifference__difference_type__idx ON public.distroseriesdifference USING btree (difference_type);


CREATE INDEX distroseriesdifference__package_diff__idx ON public.distroseriesdifference USING btree (package_diff);


CREATE INDEX distroseriesdifference__parent_package_diff__idx ON public.distroseriesdifference USING btree (parent_package_diff);


CREATE INDEX distroseriesdifference__parent_series__idx ON public.distroseriesdifference USING btree (parent_series);


CREATE INDEX distroseriesdifference__parent_source_version__idx ON public.distroseriesdifference USING btree (parent_source_version);


CREATE INDEX distroseriesdifference__source_package_name__idx ON public.distroseriesdifference USING btree (source_package_name);


CREATE INDEX distroseriesdifference__source_version__idx ON public.distroseriesdifference USING btree (source_version);


CREATE INDEX distroseriesdifference__status__idx ON public.distroseriesdifference USING btree (status);


CREATE INDEX distroseriesdifferencemessage__distroseriesdifference__idx ON public.distroseriesdifferencemessage USING btree (distro_series_difference);


CREATE INDEX distroseriespackagecache__archive__idx ON public.distroseriespackagecache USING btree (archive);


CREATE INDEX distroseriespackagecache__distroseries__idx ON public.distroseriespackagecache USING btree (distroseries);


CREATE INDEX distroseriespackagecache__fti__idx ON public.distroseriespackagecache USING gin (fti);


CREATE INDEX distroseriesparent__derived_series__ordering__idx ON public.distroseriesparent USING btree (derived_series, ordering);


CREATE INDEX distroseriesparent__parentseries__idx ON public.distroseriesparent USING btree (parent_series);


CREATE UNIQUE INDEX emailaddress__lower_email__key ON public.emailaddress USING btree (lower(email));


CREATE UNIQUE INDEX emailaddress__person__key ON public.emailaddress USING btree (person) WHERE ((status = 4) AND (person IS NOT NULL));


COMMENT ON INDEX public.emailaddress__person__key IS 'Ensures that a Person only has one preferred email address';


CREATE INDEX emailaddress__person__status__idx ON public.emailaddress USING btree (person, status);


CREATE INDEX faq__distribution__idx ON public.faq USING btree (distribution) WHERE (distribution IS NOT NULL);


CREATE INDEX faq__fti__idx ON public.faq USING gin (fti);


CREATE INDEX faq__last_updated_by__idx ON public.faq USING btree (last_updated_by);


CREATE INDEX faq__owner__idx ON public.faq USING btree (owner);


CREATE INDEX faq__product__idx ON public.faq USING btree (product) WHERE (product IS NOT NULL);


CREATE INDEX featuredproject__pillar_name__idx ON public.featuredproject USING btree (pillar_name);


CREATE INDEX featureflagchangelogentry__person__idx ON public.featureflagchangelogentry USING btree (person);


CREATE INDEX flatpackagesetinclusion__child__idx ON public.flatpackagesetinclusion USING btree (child);


CREATE INDEX gitactivity__repository__date_changed__id__idx ON public.gitactivity USING btree (repository, date_changed DESC, id DESC);


CREATE INDEX gitrepository__distribution__spn__date_last_modified__idx ON public.gitrepository USING btree (distribution, sourcepackagename, date_last_modified) WHERE (distribution IS NOT NULL);


CREATE INDEX gitrepository__distribution__spn__id__idx ON public.gitrepository USING btree (distribution, sourcepackagename, id) WHERE (distribution IS NOT NULL);


CREATE UNIQUE INDEX gitrepository__distribution__spn__target_default__key ON public.gitrepository USING btree (distribution, sourcepackagename) WHERE ((distribution IS NOT NULL) AND target_default);


CREATE INDEX gitrepository__owner__date_last_modified__idx ON public.gitrepository USING btree (owner, date_last_modified);


CREATE UNIQUE INDEX gitrepository__owner__distribution__sourcepackagename__name__ke ON public.gitrepository USING btree (owner, distribution, sourcepackagename, name) WHERE (distribution IS NOT NULL);


CREATE INDEX gitrepository__owner__distribution__spn__date_last_modified__id ON public.gitrepository USING btree (owner, distribution, sourcepackagename, date_last_modified) WHERE (distribution IS NOT NULL);


CREATE INDEX gitrepository__owner__distribution__spn__id__idx ON public.gitrepository USING btree (owner, distribution, sourcepackagename, id) WHERE (distribution IS NOT NULL);


CREATE UNIQUE INDEX gitrepository__owner__distribution__spn__owner_default__key ON public.gitrepository USING btree (owner, distribution, sourcepackagename) WHERE ((distribution IS NOT NULL) AND owner_default);


CREATE INDEX gitrepository__owner__id__idx ON public.gitrepository USING btree (owner, id);


CREATE UNIQUE INDEX gitrepository__owner__name__key ON public.gitrepository USING btree (owner, name) WHERE ((project IS NULL) AND (distribution IS NULL));


CREATE INDEX gitrepository__owner__project__date_last_modified__idx ON public.gitrepository USING btree (owner, project, date_last_modified) WHERE (project IS NOT NULL);


CREATE INDEX gitrepository__owner__project__id__idx ON public.gitrepository USING btree (owner, project, id) WHERE (project IS NOT NULL);


CREATE UNIQUE INDEX gitrepository__owner__project__name__key ON public.gitrepository USING btree (owner, project, name) WHERE (project IS NOT NULL);


CREATE UNIQUE INDEX gitrepository__owner__project__owner_default__key ON public.gitrepository USING btree (owner, project) WHERE ((project IS NOT NULL) AND owner_default);


CREATE INDEX gitrepository__project__date_last_modified__idx ON public.gitrepository USING btree (project, date_last_modified) WHERE (project IS NOT NULL);


CREATE INDEX gitrepository__project__id__idx ON public.gitrepository USING btree (project, id) WHERE (project IS NOT NULL);


CREATE UNIQUE INDEX gitrepository__project__target_default__key ON public.gitrepository USING btree (project) WHERE ((project IS NOT NULL) AND target_default);


CREATE INDEX gitrepository__registrant__idx ON public.gitrepository USING btree (registrant);


CREATE INDEX gitrepository__reviewer__idx ON public.gitrepository USING btree (reviewer);


CREATE INDEX gitrulegrant__repository__idx ON public.gitrulegrant USING btree (repository);


CREATE UNIQUE INDEX gitrulegrant__rule__grantee_type__grantee_key ON public.gitrulegrant USING btree (rule, grantee_type, grantee) WHERE (grantee_type = 2);


CREATE UNIQUE INDEX gitrulegrant__rule__grantee_type__key ON public.gitrulegrant USING btree (rule, grantee_type) WHERE (grantee_type <> 2);


CREATE UNIQUE INDEX gitsubscription__person__repository__key ON public.gitsubscription USING btree (person, repository);


CREATE INDEX gitsubscription__repository__idx ON public.gitsubscription USING btree (repository);


CREATE INDEX gitsubscription__subscribed_by__idx ON public.gitsubscription USING btree (subscribed_by);


CREATE INDEX hwdevice__bus_product_id__idx ON public.hwdevice USING btree (bus_product_id);


CREATE UNIQUE INDEX hwdevice__bus_vendor_id__bus_product_id__key ON public.hwdevice USING btree (bus_vendor_id, bus_product_id) WHERE (variant IS NULL);


CREATE INDEX hwdevice__name__idx ON public.hwdevice USING btree (name);


CREATE UNIQUE INDEX hwdeviceclass__device__main_class__key ON public.hwdeviceclass USING btree (device, main_class) WHERE (sub_class IS NULL);


CREATE UNIQUE INDEX hwdeviceclass__device__main_class__sub_class__key ON public.hwdeviceclass USING btree (device, main_class, sub_class) WHERE (sub_class IS NOT NULL);


CREATE INDEX hwdeviceclass__main_class__idx ON public.hwdeviceclass USING btree (main_class);


CREATE INDEX hwdeviceclass__sub_class__idx ON public.hwdeviceclass USING btree (sub_class);


CREATE UNIQUE INDEX hwdevicedriverlink__device__driver__key ON public.hwdevicedriverlink USING btree (device, driver) WHERE (driver IS NOT NULL);


CREATE INDEX hwdevicedriverlink__device__idx ON public.hwdevicedriverlink USING btree (device);


CREATE UNIQUE INDEX hwdevicedriverlink__device__key ON public.hwdevicedriverlink USING btree (device) WHERE (driver IS NULL);


CREATE INDEX hwdevicedriverlink__driver__idx ON public.hwdevicedriverlink USING btree (driver);


CREATE INDEX hwdevicenamevariant__device__idx ON public.hwdevicenamevariant USING btree (device);


CREATE INDEX hwdevicenamevariant__product_name__idx ON public.hwdevicenamevariant USING btree (product_name);


CREATE INDEX hwdmihandle__submission__idx ON public.hwdmihandle USING btree (submission);


CREATE INDEX hwdmivalue__hanlde__idx ON public.hwdmivalue USING btree (handle);


CREATE INDEX hwdriver__name__idx ON public.hwdriver USING btree (name);


CREATE UNIQUE INDEX hwdriver__name__key ON public.hwdriver USING btree (name) WHERE (package_name IS NULL);


CREATE INDEX hwsubmission__date_created__idx ON public.hwsubmission USING btree (date_created);


CREATE INDEX hwsubmission__date_submitted__idx ON public.hwsubmission USING btree (date_submitted);


CREATE INDEX hwsubmission__lower_raw_emailaddress__idx ON public.hwsubmission USING btree (lower(raw_emailaddress));


CREATE INDEX hwsubmission__owner__idx ON public.hwsubmission USING btree (owner);


CREATE INDEX hwsubmission__raw_emailaddress__idx ON public.hwsubmission USING btree (raw_emailaddress);


CREATE INDEX hwsubmission__raw_submission__idx ON public.hwsubmission USING btree (raw_submission);


CREATE INDEX hwsubmission__status__idx ON public.hwsubmission USING btree (status);


CREATE INDEX hwsubmission__system_fingerprint__idx ON public.hwsubmission USING btree (system_fingerprint);


CREATE INDEX hwsubmissionbug__bug ON public.hwsubmissionbug USING btree (bug);


CREATE INDEX hwsubmissiondevice__device_driver_link__idx ON public.hwsubmissiondevice USING btree (device_driver_link);


CREATE INDEX hwsubmissiondevice__parent__idx ON public.hwsubmissiondevice USING btree (parent);


CREATE INDEX hwsubmissiondevice__submission__idx ON public.hwsubmissiondevice USING btree (submission);


CREATE UNIQUE INDEX hwtest__name__version__key ON public.hwtest USING btree (name, version) WHERE (namespace IS NULL);


CREATE UNIQUE INDEX hwtest__namespace__name__version__key ON public.hwtest USING btree (namespace, name, version) WHERE (namespace IS NOT NULL);


CREATE INDEX hwtestanswer__choice__idx ON public.hwtestanswer USING btree (choice);


CREATE INDEX hwtestanswer__submission__idx ON public.hwtestanswer USING btree (submission);


CREATE INDEX hwtestanswer__test__idx ON public.hwtestanswer USING btree (test);


CREATE INDEX hwtestanswerchoice__test__idx ON public.hwtestanswerchoice USING btree (test);


CREATE INDEX hwtestanswercount__choice__idx ON public.hwtestanswercount USING btree (choice);


CREATE INDEX hwtestanswercount__distroarchrelease__idx ON public.hwtestanswercount USING btree (distroarchseries) WHERE (distroarchseries IS NOT NULL);


CREATE INDEX hwtestanswercount__test__idx ON public.hwtestanswercount USING btree (test);


CREATE INDEX hwtestanswercountdevice__device_driver__idx ON public.hwtestanswercountdevice USING btree (device_driver);


CREATE INDEX hwtestanswerdevice__device_driver__idx ON public.hwtestanswerdevice USING btree (device_driver);


CREATE INDEX hwvendorid__vendor_id_for_bus__idx ON public.hwvendorid USING btree (vendor_id_for_bus);


CREATE INDEX hwvendorid__vendorname__idx ON public.hwvendorid USING btree (vendor_name);


CREATE UNIQUE INDEX hwvendorname__lc_vendor_name__idx ON public.hwvendorname USING btree (public.ulower(name));


CREATE INDEX incrementaldiff__branch_merge_proposal__idx ON public.incrementaldiff USING btree (branch_merge_proposal);


CREATE INDEX incrementaldiff__diff__idx ON public.incrementaldiff USING btree (diff);


CREATE INDEX ircid_person_idx ON public.ircid USING btree (person);


CREATE INDEX jabberid_person_idx ON public.jabberid USING btree (person);


CREATE INDEX job__requester__key ON public.job USING btree (requester) WHERE (requester IS NOT NULL);


CREATE INDEX karma_person_datecreated_idx ON public.karma USING btree (person, datecreated);

ALTER TABLE public.karma CLUSTER ON karma_person_datecreated_idx;


CREATE INDEX karmacache__category__karmavalue__idx ON public.karmacache USING btree (category, karmavalue) WHERE ((((category IS NOT NULL) AND (product IS NULL)) AND (project IS NULL)) AND (distribution IS NULL));


CREATE INDEX karmacache__distribution__category__karmavalue__idx ON public.karmacache USING btree (distribution, category, karmavalue) WHERE (((category IS NOT NULL) AND (distribution IS NOT NULL)) AND (sourcepackagename IS NULL));


CREATE INDEX karmacache__person__category__idx ON public.karmacache USING btree (person, category);


CREATE INDEX karmacache__product__category__karmavalue__idx ON public.karmacache USING btree (product, category, karmavalue) WHERE ((category IS NOT NULL) AND (product IS NOT NULL));


CREATE INDEX karmacache__product__karmavalue__idx ON public.karmacache USING btree (product, karmavalue) WHERE ((category IS NULL) AND (product IS NOT NULL));


CREATE INDEX karmacache__project__category__karmavalue__idx ON public.karmacache USING btree (project, category, karmavalue) WHERE (project IS NOT NULL);


CREATE INDEX karmacache__project__karmavalue__idx ON public.karmacache USING btree (project, karmavalue) WHERE ((category IS NULL) AND (project IS NOT NULL));


CREATE UNIQUE INDEX karmacache__unq ON public.karmacache USING btree (person, (COALESCE(product, (-1))), (COALESCE(sourcepackagename, (-1))), (COALESCE(project, (-1))), (COALESCE(category, (-1))), (COALESCE(distribution, (-1))));


CREATE INDEX karmacache_person_idx ON public.karmacache USING btree (person);


CREATE INDEX karmacache_top_in_category_idx ON public.karmacache USING btree (person, category, karmavalue) WHERE ((((product IS NULL) AND (project IS NULL)) AND (sourcepackagename IS NULL)) AND (distribution IS NULL));


CREATE UNIQUE INDEX karmatotalcache_karma_total_person_idx ON public.karmatotalcache USING btree (karma_total, person);


CREATE INDEX languagepack__file__idx ON public.languagepack USING btree (file);


CREATE INDEX latestpersonsourcepackagereleasecache__archive__distroseries__s ON public.latestpersonsourcepackagereleasecache USING btree (upload_archive, upload_distroseries, sourcepackagename);


CREATE INDEX latestpersonsourcepackagereleasecache__archive_purpose__idx ON public.latestpersonsourcepackagereleasecache USING btree (archive_purpose);


CREATE INDEX latestpersonsourcepackagereleasecache__creator__date__non_ppa__ ON public.latestpersonsourcepackagereleasecache USING btree (creator, date_uploaded DESC) WHERE (archive_purpose <> 2);


CREATE INDEX latestpersonsourcepackagereleasecache__creator__idx ON public.latestpersonsourcepackagereleasecache USING btree (creator) WHERE (creator IS NOT NULL);


CREATE INDEX latestpersonsourcepackagereleasecache__creator__purpose__date__ ON public.latestpersonsourcepackagereleasecache USING btree (creator, archive_purpose, date_uploaded DESC);


CREATE INDEX latestpersonsourcepackagereleasecache__maintainer__date__non_pp ON public.latestpersonsourcepackagereleasecache USING btree (maintainer, date_uploaded DESC) WHERE (archive_purpose <> 2);


CREATE INDEX latestpersonsourcepackagereleasecache__maintainer__idx ON public.latestpersonsourcepackagereleasecache USING btree (maintainer) WHERE (maintainer IS NOT NULL);


CREATE INDEX latestpersonsourcepackagereleasecache__maintainer__purpose__dat ON public.latestpersonsourcepackagereleasecache USING btree (maintainer, archive_purpose, date_uploaded DESC);


CREATE INDEX libraryfilealias__content__idx ON public.libraryfilealias USING btree (content);


CREATE INDEX libraryfilealias__expires__idx ON public.libraryfilealias USING btree (expires);


CREATE INDEX libraryfilealias__expires__partial__idx ON public.libraryfilealias USING btree (expires) WHERE ((content IS NOT NULL) AND (expires IS NOT NULL));


CREATE INDEX libraryfilealias__filename__idx ON public.libraryfilealias USING btree (filename);


CREATE INDEX libraryfilecontent__md5__idx ON public.libraryfilecontent USING btree (md5);


CREATE INDEX libraryfilecontent__sha256__idx ON public.libraryfilecontent USING btree (sha256);


CREATE INDEX libraryfilecontent_sha1_filesize_idx ON public.libraryfilecontent USING btree (sha1, filesize);


CREATE INDEX livefs__distro_series__idx ON public.livefs USING btree (distro_series);


CREATE INDEX livefs__name__idx ON public.livefs USING btree (name);


CREATE INDEX livefs__owner__idx ON public.livefs USING btree (owner);


CREATE INDEX livefs__registrant__idx ON public.livefs USING btree (registrant);


CREATE INDEX livefsbuild__archive__idx ON public.livefsbuild USING btree (archive);


CREATE INDEX livefsbuild__build_farm_job__idx ON public.livefsbuild USING btree (build_farm_job);


CREATE INDEX livefsbuild__distro_arch_series__idx ON public.livefsbuild USING btree (distro_arch_series);


CREATE INDEX livefsbuild__livefs__archive__das__pocket__unique_key__status__ ON public.livefsbuild USING btree (livefs, archive, distro_arch_series, pocket, unique_key, status);


CREATE INDEX livefsbuild__livefs__das__status__finished__idx ON public.livefsbuild USING btree (livefs, distro_arch_series, status, date_finished DESC) WHERE (status = 1);


CREATE INDEX livefsbuild__livefs__idx ON public.livefsbuild USING btree (livefs);


CREATE INDEX livefsbuild__livefs__status__started__finished__created__id__id ON public.livefsbuild USING btree (livefs, status, (GREATEST(date_started, date_finished)) DESC NULLS LAST, date_created DESC, id DESC);


CREATE INDEX livefsbuild__log__idx ON public.livefsbuild USING btree (log);


CREATE INDEX livefsbuild__requester__idx ON public.livefsbuild USING btree (requester);


CREATE INDEX livefsbuild__upload_log__idx ON public.livefsbuild USING btree (upload_log);


CREATE INDEX livefsfile__libraryfile__idx ON public.livefsfile USING btree (libraryfile);


CREATE INDEX livefsfile__livefsbuild__idx ON public.livefsfile USING btree (livefsbuild);


CREATE INDEX logintoken_requester_idx ON public.logintoken USING btree (requester);


CREATE INDEX lp_openididentifier__account__idx ON public.lp_openididentifier USING btree (account);


CREATE INDEX lp_teamparticipation__person__idx ON public.lp_teamparticipation USING btree (person);


CREATE INDEX mailinglist__date_registered__idx ON public.mailinglist USING btree (status, date_registered);


CREATE INDEX mailinglist__registrant__idx ON public.mailinglist USING btree (registrant);


CREATE INDEX mailinglist__reviewer__idx ON public.mailinglist USING btree (reviewer);


CREATE UNIQUE INDEX mailinglist__team__status__key ON public.mailinglist USING btree (team, status);


CREATE INDEX mailinglistsubscription__email_address__idx ON public.mailinglistsubscription USING btree (email_address) WHERE (email_address IS NOT NULL);


CREATE INDEX mailinglistsubscription__mailing_list__idx ON public.mailinglistsubscription USING btree (mailing_list);


CREATE UNIQUE INDEX mailinglistsubscription__person__mailing_list__key ON public.mailinglistsubscription USING btree (person, mailing_list);


CREATE INDEX message__datecreated__idx ON public.message USING btree (datecreated);


CREATE INDEX message_owner_idx ON public.message USING btree (owner);


CREATE INDEX message_raw_idx ON public.message USING btree (raw) WHERE (raw IS NOT NULL);


CREATE INDEX message_rfc822msgid_idx ON public.message USING btree (rfc822msgid);


CREATE INDEX messageapproval__disposed_by__idx ON public.messageapproval USING btree (disposed_by) WHERE (disposed_by IS NOT NULL);


CREATE INDEX messageapproval__mailing_list__status__posted_date__idx ON public.messageapproval USING btree (mailing_list, status, posted_date);


CREATE INDEX messageapproval__message__idx ON public.messageapproval USING btree (message);


CREATE INDEX messageapproval__posted_by__idx ON public.messageapproval USING btree (posted_by);


CREATE INDEX messageapproval__posted_message__idx ON public.messageapproval USING btree (posted_message);


CREATE INDEX messagechunk_blob_idx ON public.messagechunk USING btree (blob) WHERE (blob IS NOT NULL);


CREATE INDEX milestone__distroseries__idx ON public.milestone USING btree (distroseries);


CREATE INDEX milestone__productseries__idx ON public.milestone USING btree (productseries);


CREATE INDEX milestone_dateexpected_name_sort ON public.milestone USING btree (public.milestone_sort_key(dateexpected, name));


CREATE INDEX milestonetag__milestones_idx ON public.milestonetag USING btree (milestone);


CREATE UNIQUE INDEX mirrordistroarchseries_uniq ON public.mirrordistroarchseries USING btree (distribution_mirror, distroarchseries, component, pocket);


CREATE UNIQUE INDEX mirrordistroseriessource_uniq ON public.mirrordistroseriessource USING btree (distribution_mirror, distroseries, component, pocket);


CREATE INDEX mirrorproberecord__distribution_mirror__date_created__idx ON public.mirrorproberecord USING btree (distribution_mirror, date_created);


CREATE INDEX mirrorproberecord__log_file__idx ON public.mirrorproberecord USING btree (log_file) WHERE (log_file IS NOT NULL);


CREATE INDEX oauthaccesstoken__person__idx ON public.oauthaccesstoken USING btree (person);


CREATE INDEX oauthrequesttoken__person__idx ON public.oauthrequesttoken USING btree (person) WHERE (person IS NOT NULL);


CREATE UNIQUE INDEX officialbugtag__distribution__tag__key ON public.officialbugtag USING btree (distribution, tag) WHERE (distribution IS NOT NULL);


CREATE UNIQUE INDEX officialbugtag__product__tag__key ON public.officialbugtag USING btree (product, tag) WHERE (product IS NOT NULL);


CREATE UNIQUE INDEX officialbugtag__project__tag__key ON public.officialbugtag USING btree (project, tag) WHERE (product IS NOT NULL);


CREATE INDEX openididentifier__account__idx ON public.openididentifier USING btree (account);


CREATE UNIQUE INDEX packagecopyjob__job_type__target_ds__id__key ON public.packagecopyjob USING btree (job_type, target_distroseries, id);


CREATE INDEX packagecopyjob__target ON public.packagecopyjob USING btree (target_archive, target_distroseries);


CREATE INDEX packagecopyrequest__datecreated__idx ON public.packagecopyrequest USING btree (date_created);


CREATE INDEX packagecopyrequest__requester__idx ON public.packagecopyrequest USING btree (requester);


CREATE INDEX packagecopyrequest__targetarchive__idx ON public.packagecopyrequest USING btree (target_archive);


CREATE INDEX packagecopyrequest__targetdistroseries__idx ON public.packagecopyrequest USING btree (target_distroseries) WHERE (target_distroseries IS NOT NULL);


CREATE INDEX packagediff__diff_content__idx ON public.packagediff USING btree (diff_content);


CREATE INDEX packagediff__from_source__idx ON public.packagediff USING btree (from_source);


CREATE UNIQUE INDEX packagediff__from_source__to_source__key ON public.packagediff USING btree (from_source, to_source);


CREATE INDEX packagediff__requester__idx ON public.packagediff USING btree (requester);


CREATE INDEX packagediff__status__idx ON public.packagediff USING btree (status);


CREATE INDEX packagediff__to_source__idx ON public.packagediff USING btree (to_source);


CREATE INDEX packageset__distroseries__idx ON public.packageset USING btree (distroseries);


CREATE INDEX packageset__owner__idx ON public.packageset USING btree (owner);


CREATE INDEX packageset__packagesetgroup__idx ON public.packageset USING btree (packagesetgroup);


CREATE INDEX packagesetgroup__owner__idx ON public.packagesetgroup USING btree (owner);


CREATE INDEX packagesetinclusion__child__idx ON public.packagesetinclusion USING btree (child);


CREATE INDEX packagesetsources__sourcepackagename__idx ON public.packagesetsources USING btree (sourcepackagename);


CREATE INDEX packageupload__archive__distroseries__status__idx ON public.packageupload USING btree (archive, distroseries, status);


CREATE INDEX packageupload__changesfile__idx ON public.packageupload USING btree (changesfile);


CREATE INDEX packageupload__distroseries__key ON public.packageupload USING btree (distroseries);


CREATE INDEX packageupload__distroseries__status__idx ON public.packageupload USING btree (distroseries, status);


CREATE INDEX packageupload__package_copy_job__idx ON public.packageupload USING btree (package_copy_job) WHERE (package_copy_job IS NOT NULL);


CREATE INDEX packageupload__searchable_names__idx ON public.packageupload USING gin (((searchable_names)::tsvector));


CREATE INDEX packageupload__searchable_versions__idx ON public.packageupload USING gin (searchable_versions);


CREATE INDEX packageupload__signing_key_fingerprint__idx ON public.packageupload USING btree (signing_key_fingerprint);


CREATE INDEX packageupload__signing_key_owner__idx ON public.packageupload USING btree (signing_key_owner);


CREATE INDEX packageuploadbuild__build__idx ON public.packageuploadbuild USING btree (build);


CREATE INDEX packageuploadcustom__libraryfilealias__idx ON public.packageuploadcustom USING btree (libraryfilealias);


CREATE INDEX packageuploadcustom__packageupload__idx ON public.packageuploadcustom USING btree (packageupload);


CREATE INDEX packageuploadsource__sourcepackagerelease__idx ON public.packageuploadsource USING btree (sourcepackagerelease);


CREATE INDEX packaging__owner__idx ON public.packaging USING btree (owner);


CREATE INDEX packaging__productseries__idx ON public.packaging USING btree (productseries);


CREATE INDEX packaging_sourcepackagename_idx ON public.packaging USING btree (sourcepackagename);


CREATE INDEX packagingjob__job__idx ON public.packagingjob USING btree (job);


CREATE INDEX packagingjob__potemplate__idx ON public.packagingjob USING btree (potemplate);


CREATE INDEX parsedapachelog__first_line__idx ON public.parsedapachelog USING btree (first_line);


CREATE INDEX person__displayname__idx ON public.person USING btree (lower(displayname));


CREATE INDEX person__fti__idx ON public.person USING gin (fti);


CREATE INDEX person__icon__idx ON public.person USING btree (icon) WHERE (icon IS NOT NULL);


CREATE INDEX person__logo__idx ON public.person USING btree (logo) WHERE (logo IS NOT NULL);


CREATE INDEX person__merged__idx ON public.person USING btree (merged) WHERE (merged IS NOT NULL);


CREATE INDEX person__mugshot__idx ON public.person USING btree (mugshot) WHERE (mugshot IS NOT NULL);


CREATE INDEX person__registrant__idx ON public.person USING btree (registrant);


CREATE INDEX person__teamowner__idx ON public.person USING btree (teamowner) WHERE (teamowner IS NOT NULL);


CREATE INDEX person_datecreated_idx ON public.person USING btree (datecreated);


CREATE INDEX person_sorting_idx ON public.person USING btree (public.person_sort_key(displayname, name));


CREATE INDEX personlocation__last_modified_by__idx ON public.personlocation USING btree (last_modified_by);


CREATE INDEX personnotification__date_emailed__idx ON public.personnotification USING btree (date_emailed);


CREATE INDEX personnotification__person__idx ON public.personnotification USING btree (person);


CREATE INDEX persontransferjob__major_person__idx ON public.persontransferjob USING btree (major_person);


CREATE INDEX persontransferjob__minor_person__idx ON public.persontransferjob USING btree (minor_person);


CREATE INDEX pillarname__alias_for__idx ON public.pillarname USING btree (alias_for) WHERE (alias_for IS NOT NULL);


CREATE UNIQUE INDEX pillarname__distribution__key ON public.pillarname USING btree (distribution) WHERE (distribution IS NOT NULL);


CREATE UNIQUE INDEX pillarname__product__key ON public.pillarname USING btree (product) WHERE (product IS NOT NULL);


CREATE UNIQUE INDEX pillarname__project__key ON public.pillarname USING btree (project) WHERE (project IS NOT NULL);


CREATE INDEX pocketchroot__chroot__idx ON public.pocketchroot USING btree (chroot);


CREATE INDEX poexportrequest__person__idx ON public.poexportrequest USING btree (person);


CREATE UNIQUE INDEX poexportrequest_duplicate_key ON public.poexportrequest USING btree (potemplate, person, format, (COALESCE(pofile, (-1))));


CREATE INDEX pofile__from_sourcepackagename__idx ON public.pofile USING btree (from_sourcepackagename) WHERE (from_sourcepackagename IS NOT NULL);


CREATE UNIQUE INDEX pofile__potemplate__language__idx ON public.pofile USING btree (potemplate, language);


CREATE UNIQUE INDEX pofile__potemplate__path__key ON public.pofile USING btree (potemplate, path);


CREATE UNIQUE INDEX pofile__unreviewed_count__id__key ON public.pofile USING btree (unreviewed_count, id);


CREATE INDEX pofile_language_idx ON public.pofile USING btree (language);


CREATE INDEX pofile_lasttranslator_idx ON public.pofile USING btree (lasttranslator);


CREATE INDEX pofile_owner_idx ON public.pofile USING btree (owner);


CREATE INDEX pofiletranslator__date_last_touched__idx ON public.pofiletranslator USING btree (date_last_touched);


CREATE INDEX pofiletranslator__pofile__idx ON public.pofiletranslator USING btree (pofile);


CREATE INDEX polloption_poll_idx ON public.polloption USING btree (poll);


CREATE UNIQUE INDEX pomsgid_msgid_key ON public.pomsgid USING btree (public.sha1(msgid));


CREATE UNIQUE INDEX potemplate__distroseries__sourcepackagename__name__key ON public.potemplate USING btree (distroseries, sourcepackagename, name);


CREATE INDEX potemplate__name__idx ON public.potemplate USING btree (name);


CREATE UNIQUE INDEX potemplate__productseries__name__key ON public.potemplate USING btree (productseries, name);


CREATE INDEX potemplate__source_file__idx ON public.potemplate USING btree (source_file) WHERE (source_file IS NOT NULL);


CREATE INDEX potemplate_languagepack_idx ON public.potemplate USING btree (languagepack);


CREATE INDEX potemplate_owner_idx ON public.potemplate USING btree (owner);


CREATE INDEX potmsgset__context__msgid_singular__msgid_plural__idx ON public.potmsgset USING btree (context, msgid_singular, msgid_plural) WHERE ((context IS NOT NULL) AND (msgid_plural IS NOT NULL));


CREATE INDEX potmsgset__context__msgid_singular__no_msgid_plural__idx ON public.potmsgset USING btree (context, msgid_singular) WHERE ((context IS NOT NULL) AND (msgid_plural IS NULL));


CREATE INDEX potmsgset__no_context__msgid_singular__msgid_plural__idx ON public.potmsgset USING btree (msgid_singular, msgid_plural) WHERE ((context IS NULL) AND (msgid_plural IS NOT NULL));


CREATE INDEX potmsgset__no_context__msgid_singular__no_msgid_plural__idx ON public.potmsgset USING btree (msgid_singular) WHERE ((context IS NULL) AND (msgid_plural IS NULL));


CREATE INDEX potmsgset_primemsgid_idx ON public.potmsgset USING btree (msgid_singular);


CREATE UNIQUE INDEX potranslation_translation_key ON public.potranslation USING btree (public.sha1(translation));


CREATE UNIQUE INDEX previewdiff__branch_merge_proposal__date_created__key ON public.previewdiff USING btree (branch_merge_proposal, date_created);


CREATE INDEX previewdiff__diff__idx ON public.previewdiff USING btree (diff);


CREATE INDEX product__bug_supervisor__idx ON public.product USING btree (bug_supervisor) WHERE (bug_supervisor IS NOT NULL);


CREATE INDEX product__datecreated__id__idx ON public.product USING btree (datecreated, id DESC);


CREATE INDEX product__driver__idx ON public.product USING btree (driver) WHERE (driver IS NOT NULL);


CREATE INDEX product__fti__idx ON public.product USING gin (fti);


CREATE INDEX product__icon__idx ON public.product USING btree (icon) WHERE (icon IS NOT NULL);


CREATE INDEX product__information_type__idx ON public.product USING btree (information_type);


CREATE INDEX product__logo__idx ON public.product USING btree (logo) WHERE (logo IS NOT NULL);


CREATE INDEX product__mugshot__idx ON public.product USING btree (mugshot) WHERE (mugshot IS NOT NULL);


CREATE INDEX product__registrant__idx ON public.product USING btree (registrant);


CREATE INDEX product_active_idx ON public.product USING btree (active);


CREATE INDEX product_owner_idx ON public.product USING btree (owner);


CREATE INDEX product_project_idx ON public.product USING btree (project);


CREATE INDEX product_translationgroup_idx ON public.product USING btree (translationgroup);


CREATE INDEX productjob__job_type_idx ON public.productjob USING btree (job_type);


CREATE INDEX productrelease_owner_idx ON public.productrelease USING btree (owner);


CREATE INDEX productreleasefile__fti__idx ON public.productreleasefile USING gin (fti);


CREATE INDEX productreleasefile__libraryfile__idx ON public.productreleasefile USING btree (libraryfile);


CREATE INDEX productreleasefile__productrelease__idx ON public.productreleasefile USING btree (productrelease);


CREATE INDEX productreleasefile__signature__idx ON public.productreleasefile USING btree (signature) WHERE (signature IS NOT NULL);


CREATE INDEX productreleasefile__uploader__idx ON public.productreleasefile USING btree (uploader);


CREATE INDEX productseries__branch__idx ON public.productseries USING btree (branch) WHERE (branch IS NOT NULL);


CREATE INDEX productseries__driver__idx ON public.productseries USING btree (driver);


CREATE INDEX productseries__owner__idx ON public.productseries USING btree (owner);


CREATE INDEX productseries__translations_branch__idx ON public.productseries USING btree (translations_branch);


CREATE INDEX productseries_name_sort ON public.productseries USING btree (public.version_sort_key(name));


CREATE INDEX project__driver__idx ON public.project USING btree (driver);


CREATE INDEX project__fti__idx ON public.project USING gin (fti);


CREATE INDEX project__icon__idx ON public.project USING btree (icon) WHERE (icon IS NOT NULL);


CREATE INDEX project__logo__idx ON public.project USING btree (logo) WHERE (logo IS NOT NULL);


CREATE INDEX project__mugshot__idx ON public.project USING btree (mugshot) WHERE (mugshot IS NOT NULL);


CREATE INDEX project__registrant__idx ON public.project USING btree (registrant);


CREATE INDEX project_owner_idx ON public.project USING btree (owner);


CREATE INDEX project_translationgroup_idx ON public.project USING btree (translationgroup);


CREATE UNIQUE INDEX publisherconfig__distribution__idx ON public.publisherconfig USING btree (distribution);


CREATE INDEX question__answerer__idx ON public.question USING btree (answerer);


CREATE INDEX question__assignee__idx ON public.question USING btree (assignee);


CREATE INDEX question__datecreated__idx ON public.question USING btree (datecreated);


CREATE INDEX question__distribution__sourcepackagename__idx ON public.question USING btree (distribution, sourcepackagename);


CREATE INDEX question__distro__datecreated__idx ON public.question USING btree (distribution, datecreated);


CREATE INDEX question__faq__idx ON public.question USING btree (faq) WHERE (faq IS NOT NULL);


CREATE INDEX question__fti__idx ON public.question USING gin (fti);


CREATE INDEX question__owner__idx ON public.question USING btree (owner);


CREATE INDEX question__product__datecreated__idx ON public.question USING btree (product, datecreated);


CREATE INDEX question__product__idx ON public.question USING btree (product);


CREATE INDEX question__status__datecreated__idx ON public.question USING btree (status, datecreated);


CREATE INDEX questionmessage__owner__idx ON public.questionmessage USING btree (owner);


CREATE INDEX questionmessage__question__idx ON public.questionmessage USING btree (question);


CREATE INDEX questionreopening__answerer__idx ON public.questionreopening USING btree (answerer);


CREATE INDEX questionreopening__question__idx ON public.questionreopening USING btree (question);


CREATE INDEX questionreopening__reopener__idx ON public.questionreopening USING btree (reopener);


CREATE INDEX questionsubscription__subscriber__idx ON public.questionsubscription USING btree (person);


CREATE INDEX revision__revision_author__idx ON public.revision USING btree (revision_author);


CREATE INDEX revision__revision_date__idx ON public.revision USING btree (revision_date);


CREATE INDEX revision__signing_key_fingerprint__idx ON public.revision USING btree (signing_key_fingerprint);


CREATE INDEX revision__signing_key_owner__idx ON public.revision USING btree (signing_key_owner);


CREATE INDEX revisionauthor__person__idx ON public.revisionauthor USING btree (person);


CREATE UNIQUE INDEX revisioncache__distroseries__sourcepackagename__revision__priva ON public.revisioncache USING btree (distroseries, sourcepackagename, revision, private) WHERE (distroseries IS NOT NULL);


CREATE UNIQUE INDEX revisioncache__product__revision__private__key ON public.revisioncache USING btree (product, revision, private) WHERE (product IS NOT NULL);


CREATE INDEX revisioncache__revision_date__idx ON public.revisioncache USING btree (revision_date);


CREATE INDEX scriptactivity__hostname__name__date_completed__idx ON public.scriptactivity USING btree (hostname, name, date_completed);

ALTER TABLE public.scriptactivity CLUSTER ON scriptactivity__hostname__name__date_completed__idx;


CREATE INDEX scriptactivity__name__date_started__idx ON public.scriptactivity USING btree (name, date_started);


CREATE INDEX securebinarypackagepublishinghistory__archive__status__idx ON public.binarypackagepublishinghistory USING btree (archive, status);


CREATE INDEX securebinarypackagepublishinghistory__distroarchseries__idx ON public.binarypackagepublishinghistory USING btree (distroarchseries);


CREATE INDEX securebinarypackagepublishinghistory__removed_by__idx ON public.binarypackagepublishinghistory USING btree (removed_by) WHERE (removed_by IS NOT NULL);


CREATE INDEX securebinarypackagepublishinghistory_binarypackagerelease_idx ON public.binarypackagepublishinghistory USING btree (binarypackagerelease);


CREATE INDEX securebinarypackagepublishinghistory_component_idx ON public.binarypackagepublishinghistory USING btree (component);


CREATE INDEX securebinarypackagepublishinghistory_pocket_idx ON public.binarypackagepublishinghistory USING btree (pocket);


CREATE INDEX securesourcepackagepublishinghistory__archive__status__idx ON public.sourcepackagepublishinghistory USING btree (archive, status);


CREATE INDEX securesourcepackagepublishinghistory__distroseries__idx ON public.sourcepackagepublishinghistory USING btree (distroseries);


CREATE INDEX securesourcepackagepublishinghistory__removed_by__idx ON public.sourcepackagepublishinghistory USING btree (removed_by) WHERE (removed_by IS NOT NULL);


CREATE INDEX securesourcepackagepublishinghistory_component_idx ON public.sourcepackagepublishinghistory USING btree (component);


CREATE INDEX securesourcepackagepublishinghistory_pocket_idx ON public.sourcepackagepublishinghistory USING btree (pocket);


CREATE INDEX securesourcepackagepublishinghistory_sourcepackagerelease_idx ON public.sourcepackagepublishinghistory USING btree (sourcepackagerelease);


CREATE INDEX securesourcepackagepublishinghistory_status_idx ON public.sourcepackagepublishinghistory USING btree (status);


CREATE INDEX seriessourcepackagebranch__branch__idx ON public.seriessourcepackagebranch USING btree (branch);


CREATE INDEX seriessourcepackagebranch__registrant__key ON public.seriessourcepackagebranch USING btree (registrant);


CREATE INDEX sharingjob__grantee__idx ON public.sharingjob USING btree (grantee);


CREATE INDEX signedcodeofconduct__signing_key_fingerprint__idx ON public.signedcodeofconduct USING btree (signing_key_fingerprint);


CREATE INDEX signedcodeofconduct_owner_idx ON public.signedcodeofconduct USING btree (owner);


CREATE INDEX snap__branch__idx ON public.snap USING btree (branch);


CREATE INDEX snap__distro_series__idx ON public.snap USING btree (distro_series);


CREATE INDEX snap__git_repository__idx ON public.snap USING btree (git_repository);


CREATE INDEX snap__registrant__idx ON public.snap USING btree (registrant);


CREATE INDEX snap__store_series__idx ON public.snap USING btree (store_series) WHERE (store_series IS NOT NULL);


CREATE UNIQUE INDEX snapbase__is_default__idx ON public.snapbase USING btree (is_default) WHERE is_default;


CREATE UNIQUE INDEX snapbase__name__key ON public.snapbase USING btree (name);


CREATE INDEX snapbase__registrant__idx ON public.snapbase USING btree (registrant);


CREATE INDEX snapbuild__archive__idx ON public.snapbuild USING btree (archive);


CREATE INDEX snapbuild__build_farm_job__idx ON public.snapbuild USING btree (build_farm_job);


CREATE INDEX snapbuild__distro_arch_series__idx ON public.snapbuild USING btree (distro_arch_series);


CREATE INDEX snapbuild__log__idx ON public.snapbuild USING btree (log);


CREATE INDEX snapbuild__requester__idx ON public.snapbuild USING btree (requester);


CREATE INDEX snapbuild__snap__archive__das__pocket__status__idx ON public.snapbuild USING btree (snap, archive, distro_arch_series, pocket, status);


CREATE INDEX snapbuild__snap__das__status__finished__idx ON public.snapbuild USING btree (snap, distro_arch_series, status, date_finished DESC) WHERE (status = 1);


CREATE INDEX snapbuild__snap__idx ON public.snapbuild USING btree (snap);


CREATE INDEX snapbuild__snap__status__started__finished__created__id__idx ON public.snapbuild USING btree (snap, status, (GREATEST(date_started, date_finished)) DESC NULLS LAST, date_created DESC, id DESC);


CREATE INDEX snapbuild__upload_log__idx ON public.snapbuild USING btree (upload_log);


CREATE INDEX snapbuildjob__snapbuild__job_type__job__idx ON public.snapbuildjob USING btree (snapbuild, job_type, job);


CREATE INDEX snapfile__libraryfile__idx ON public.snapfile USING btree (libraryfile);


CREATE INDEX snapfile__snapbuild__idx ON public.snapfile USING btree (snapbuild);


CREATE INDEX snapjob__snap__job_type__job__idx ON public.snapjob USING btree (snap, job_type, job);


CREATE INDEX snappydistroseries__distro_series__idx ON public.snappydistroseries USING btree (distro_series);


CREATE UNIQUE INDEX snappydistroseries__snappy_series__distro_series__idx ON public.snappydistroseries USING btree (snappy_series, distro_series);


CREATE UNIQUE INDEX snappydistroseries__snappy_series__guess_distro_series__idx ON public.snappydistroseries USING btree (snappy_series) WHERE (distro_series IS NULL);


CREATE UNIQUE INDEX snappydistroseries__snappy_series__preferred__idx ON public.snappydistroseries USING btree (snappy_series) WHERE preferred;


CREATE UNIQUE INDEX snappyseries__name__key ON public.snappyseries USING btree (name);


CREATE INDEX snappyseries__registrant__idx ON public.snappyseries USING btree (registrant);


CREATE INDEX snappyseries__status__idx ON public.snappyseries USING btree (status);


CREATE INDEX sourcepackagename__name__trgm ON public.sourcepackagename USING gin (name trgm.gin_trgm_ops);


CREATE INDEX sourcepackagepublishinghistory__archive__distroseries__componen ON public.sourcepackagepublishinghistory USING btree (archive, distroseries, component, sourcepackagename) WHERE (status = ANY (ARRAY[1, 2]));


CREATE INDEX sourcepackagepublishinghistory__archive__distroseries__spn__sta ON public.sourcepackagepublishinghistory USING btree (archive, distroseries, sourcepackagename, status);


CREATE INDEX sourcepackagepublishinghistory__archive__spn__status__idx ON public.sourcepackagepublishinghistory USING btree (archive, sourcepackagename, status);


CREATE INDEX sourcepackagepublishinghistory__archive__status__scheduleddelet ON public.sourcepackagepublishinghistory USING btree (archive, status) WHERE (scheduleddeletiondate IS NULL);


CREATE INDEX sourcepackagepublishinghistory__creator__idx ON public.sourcepackagepublishinghistory USING btree (creator) WHERE (creator IS NOT NULL);


CREATE INDEX sourcepackagepublishinghistory__datecreated__id__idx ON public.sourcepackagepublishinghistory USING btree (datecreated, id);


CREATE INDEX sourcepackagepublishinghistory__packageupload__idx ON public.sourcepackagepublishinghistory USING btree (packageupload);


CREATE INDEX sourcepackagepublishinghistory__sourcepackagename__idx ON public.sourcepackagepublishinghistory USING btree (sourcepackagename);


CREATE INDEX sourcepackagepublishinghistory__sponsor__idx ON public.sourcepackagepublishinghistory USING btree (sponsor) WHERE (sponsor IS NOT NULL);


CREATE INDEX sourcepackagerecipe__daily_build_archive__idx ON public.sourcepackagerecipe USING btree (daily_build_archive);


CREATE INDEX sourcepackagerecipe__is_stale__build_daily__idx ON public.sourcepackagerecipe USING btree (is_stale, build_daily);


CREATE INDEX sourcepackagerecipe__registrant__idx ON public.sourcepackagerecipe USING btree (registrant);


CREATE INDEX sourcepackagerecipebuild__build_farm_job__idx ON public.sourcepackagerecipebuild USING btree (build_farm_job);


CREATE INDEX sourcepackagerecipebuild__distroseries__idx ON public.sourcepackagerecipebuild USING btree (distroseries);


CREATE INDEX sourcepackagerecipebuild__log__idx ON public.sourcepackagerecipebuild USING btree (log);


CREATE INDEX sourcepackagerecipebuild__manifest__idx ON public.sourcepackagerecipebuild USING btree (manifest);


CREATE INDEX sourcepackagerecipebuild__recipe__date_created__idx ON public.sourcepackagerecipebuild USING btree (recipe, date_created DESC);


CREATE INDEX sourcepackagerecipebuild__recipe__date_finished__idx ON public.sourcepackagerecipebuild USING btree (recipe, date_finished DESC);


CREATE INDEX sourcepackagerecipebuild__recipe__started__finished__created__i ON public.sourcepackagerecipebuild USING btree (recipe, (GREATEST(date_started, date_finished)) DESC NULLS LAST, date_created DESC, id DESC);


CREATE INDEX sourcepackagerecipebuild__recipe__started__finished__idx ON public.sourcepackagerecipebuild USING btree (recipe, (GREATEST(date_started, date_finished)) DESC NULLS LAST, id DESC);


CREATE INDEX sourcepackagerecipebuild__recipe__status__id__idx ON public.sourcepackagerecipebuild USING btree (recipe, status, id DESC);


CREATE INDEX sourcepackagerecipebuild__requester__idx ON public.sourcepackagerecipebuild USING btree (requester);


CREATE INDEX sourcepackagerecipebuild__upload_log__idx ON public.sourcepackagerecipebuild USING btree (upload_log);


CREATE INDEX sourcepackagerecipedata__base_branch__idx ON public.sourcepackagerecipedata USING btree (base_branch) WHERE (base_branch IS NOT NULL);


CREATE INDEX sourcepackagerecipedata__base_git_repository__idx ON public.sourcepackagerecipedata USING btree (base_git_repository) WHERE (base_git_repository IS NOT NULL);


CREATE UNIQUE INDEX sourcepackagerecipedata__sourcepackage_recipe__key ON public.sourcepackagerecipedata USING btree (sourcepackage_recipe) WHERE (sourcepackage_recipe IS NOT NULL);


CREATE UNIQUE INDEX sourcepackagerecipedata__sourcepackage_recipe_build__key ON public.sourcepackagerecipedata USING btree (sourcepackage_recipe_build) WHERE (sourcepackage_recipe_build IS NOT NULL);


CREATE INDEX sourcepackagerecipedatainstruction__branch__idx ON public.sourcepackagerecipedatainstruction USING btree (branch);


CREATE INDEX sourcepackagerelease__buildinfo__idx ON public.sourcepackagerelease USING btree (buildinfo);


CREATE INDEX sourcepackagerelease__changelog__idx ON public.sourcepackagerelease USING btree (changelog);


CREATE INDEX sourcepackagerelease__signing_key_fingerprint__idx ON public.sourcepackagerelease USING btree (signing_key_fingerprint);


CREATE INDEX sourcepackagerelease__signing_key_owner__idx ON public.sourcepackagerelease USING btree (signing_key_owner);


CREATE INDEX sourcepackagerelease__sourcepackage_recipe_build__idx ON public.sourcepackagerelease USING btree (sourcepackage_recipe_build);


CREATE INDEX sourcepackagerelease__sourcepackagename__version__idx ON public.sourcepackagerelease USING btree (sourcepackagename, version);


CREATE INDEX sourcepackagerelease__upload_archive__idx ON public.sourcepackagerelease USING btree (upload_archive);


CREATE INDEX sourcepackagerelease_creator_idx ON public.sourcepackagerelease USING btree (creator);


CREATE INDEX sourcepackagerelease_maintainer_idx ON public.sourcepackagerelease USING btree (maintainer);


CREATE INDEX sourcepackagerelease_sourcepackagename_idx ON public.sourcepackagerelease USING btree (sourcepackagename);


CREATE INDEX sourcepackagereleasefile_libraryfile_idx ON public.sourcepackagereleasefile USING btree (libraryfile);


CREATE INDEX sourcepackagereleasefile_sourcepackagerelease_idx ON public.sourcepackagereleasefile USING btree (sourcepackagerelease);


CREATE INDEX specification__completer__idx ON public.specification USING btree (completer);


CREATE INDEX specification__date_last_changed__idx ON public.specification USING btree (date_last_changed);


CREATE INDEX specification__datecreated__id__idx ON public.specification USING btree (datecreated, id DESC);


CREATE INDEX specification__distroseries__idx ON public.specification USING btree (distroseries);


CREATE INDEX specification__fti__idx ON public.specification USING gin (fti);


CREATE INDEX specification__goal_decider__idx ON public.specification USING btree (goal_decider);


CREATE INDEX specification__goal_proposer__idx ON public.specification USING btree (goal_proposer);


CREATE INDEX specification__information_type__idx ON public.specification USING btree (information_type);


CREATE INDEX specification__last_changed_by__idx ON public.specification USING btree (last_changed_by) WHERE (last_changed_by IS NOT NULL);


CREATE INDEX specification__milestone__idx ON public.specification USING btree (milestone);


CREATE UNIQUE INDEX specification__product__name__key ON public.specification USING btree (product, name);


CREATE INDEX specification__productseries__idx ON public.specification USING btree (productseries);


CREATE INDEX specification__starter__idx ON public.specification USING btree (starter);


CREATE INDEX specification_approver_idx ON public.specification USING btree (approver);


CREATE INDEX specification_assignee_idx ON public.specification USING btree (assignee);


CREATE INDEX specification_drafter_idx ON public.specification USING btree (drafter);


CREATE INDEX specification_owner_idx ON public.specification USING btree (owner);


CREATE INDEX specificationbranch__registrant__idx ON public.specificationbranch USING btree (registrant);


CREATE INDEX specificationbranch__specification__idx ON public.specificationbranch USING btree (specification);


CREATE INDEX specificationdependency_dependency_idx ON public.specificationdependency USING btree (dependency);


CREATE INDEX specificationdependency_specification_idx ON public.specificationdependency USING btree (specification);


CREATE INDEX specificationsubscription_specification_idx ON public.specificationsubscription USING btree (specification);


CREATE INDEX specificationsubscription_subscriber_idx ON public.specificationsubscription USING btree (person);


CREATE INDEX specificationworkitem__assignee__idx ON public.specificationworkitem USING btree (assignee) WHERE (assignee IS NOT NULL);


CREATE INDEX specificationworkitem__milestone__idx ON public.specificationworkitem USING btree (milestone);


CREATE INDEX specificationworkitem__specification__sequence__idx ON public.specificationworkitem USING btree (specification, sequence);


CREATE INDEX sprint__driver__idx ON public.sprint USING btree (driver);


CREATE INDEX sprint__icon__idx ON public.sprint USING btree (icon) WHERE (icon IS NOT NULL);


CREATE INDEX sprint__logo__idx ON public.sprint USING btree (logo) WHERE (logo IS NOT NULL);


CREATE INDEX sprint__mugshot__idx ON public.sprint USING btree (mugshot) WHERE (mugshot IS NOT NULL);


CREATE INDEX sprint__owner__idx ON public.sprint USING btree (owner);


CREATE INDEX sprint_datecreated_idx ON public.sprint USING btree (datecreated);


CREATE INDEX sprintattendance_sprint_idx ON public.sprintattendance USING btree (sprint);


CREATE INDEX sprintspec_sprint_idx ON public.sprintspecification USING btree (sprint);


CREATE INDEX sprintspecification__decider__idx ON public.sprintspecification USING btree (decider);


CREATE INDEX sprintspecification__registrant__idx ON public.sprintspecification USING btree (registrant);


CREATE INDEX sshkey_person_key ON public.sshkey USING btree (person);


CREATE UNIQUE INDEX structuralsubscription__distribution__sourcepackagename__subscr ON public.structuralsubscription USING btree (distribution, sourcepackagename, subscriber) WHERE ((distribution IS NOT NULL) AND (sourcepackagename IS NOT NULL));


CREATE UNIQUE INDEX structuralsubscription__distribution__subscriber__key ON public.structuralsubscription USING btree (distribution, subscriber) WHERE ((distribution IS NOT NULL) AND (sourcepackagename IS NULL));


CREATE UNIQUE INDEX structuralsubscription__distroseries__subscriber__key ON public.structuralsubscription USING btree (distroseries, subscriber) WHERE (distroseries IS NOT NULL);


CREATE UNIQUE INDEX structuralsubscription__milestone__subscriber__key ON public.structuralsubscription USING btree (milestone, subscriber) WHERE (milestone IS NOT NULL);


CREATE UNIQUE INDEX structuralsubscription__product__subscriber__key ON public.structuralsubscription USING btree (product, subscriber) WHERE (product IS NOT NULL);


CREATE UNIQUE INDEX structuralsubscription__productseries__subscriber__key ON public.structuralsubscription USING btree (productseries, subscriber) WHERE (productseries IS NOT NULL);


CREATE UNIQUE INDEX structuralsubscription__project__subscriber__key ON public.structuralsubscription USING btree (project, subscriber) WHERE (project IS NOT NULL);


CREATE INDEX structuralsubscription__subscribed_by__idx ON public.structuralsubscription USING btree (subscribed_by);


CREATE INDEX structuralsubscription__subscriber__idx ON public.structuralsubscription USING btree (subscriber);


CREATE INDEX teammembership__acknowledged_by__idx ON public.teammembership USING btree (acknowledged_by) WHERE (acknowledged_by IS NOT NULL);


CREATE INDEX teammembership__last_changed_by__idx ON public.teammembership USING btree (last_changed_by) WHERE (last_changed_by IS NOT NULL);


CREATE INDEX teammembership__proposed_by__idx ON public.teammembership USING btree (proposed_by) WHERE (proposed_by IS NOT NULL);


CREATE INDEX teammembership__reviewed_by__idx ON public.teammembership USING btree (reviewed_by) WHERE (reviewed_by IS NOT NULL);


CREATE INDEX teammembership__team__idx ON public.teammembership USING btree (team);


CREATE INDEX teamparticipation_person_idx ON public.teamparticipation USING btree (person);

ALTER TABLE public.teamparticipation CLUSTER ON teamparticipation_person_idx;


CREATE UNIQUE INDEX tm__potmsgset__language__shared__ubuntu__key ON public.translationmessage USING btree (potmsgset, language) WHERE ((is_current_ubuntu IS TRUE) AND (potemplate IS NULL));


CREATE UNIQUE INDEX tm__potmsgset__language__shared__upstream__key ON public.translationmessage USING btree (potmsgset, language) WHERE ((is_current_upstream IS TRUE) AND (potemplate IS NULL));


CREATE UNIQUE INDEX tm__potmsgset__template__language__diverged__ubuntu__key ON public.translationmessage USING btree (potmsgset, potemplate, language) WHERE ((is_current_ubuntu IS TRUE) AND (potemplate IS NOT NULL));


CREATE UNIQUE INDEX tm__potmsgset__template__language__diverged__upstream__key ON public.translationmessage USING btree (potmsgset, potemplate, language) WHERE ((is_current_upstream IS TRUE) AND (potemplate IS NOT NULL));


CREATE INDEX translationgroup__owner__idx ON public.translationgroup USING btree (owner);


CREATE INDEX translationimportqueueentry__content__idx ON public.translationimportqueueentry USING btree (content) WHERE (content IS NOT NULL);


CREATE INDEX translationimportqueueentry__context__path__idx ON public.translationimportqueueentry USING btree (distroseries, sourcepackagename, productseries, path);


CREATE UNIQUE INDEX translationimportqueueentry__entry_per_importer__unq ON public.translationimportqueueentry USING btree (importer, path, (COALESCE(potemplate, (-1))), (COALESCE(distroseries, (-1))), (COALESCE(sourcepackagename, (-1))), (COALESCE(productseries, (-1))));


CREATE INDEX translationimportqueueentry__path__idx ON public.translationimportqueueentry USING btree (path);


CREATE INDEX translationimportqueueentry__pofile__idx ON public.translationimportqueueentry USING btree (pofile) WHERE (pofile IS NOT NULL);


CREATE INDEX translationimportqueueentry__potemplate__idx ON public.translationimportqueueentry USING btree (potemplate) WHERE (potemplate IS NOT NULL);


CREATE INDEX translationimportqueueentry__productseries__idx ON public.translationimportqueueentry USING btree (productseries) WHERE (productseries IS NOT NULL);


CREATE INDEX translationimportqueueentry__sourcepackagename__idx ON public.translationimportqueueentry USING btree (sourcepackagename) WHERE (sourcepackagename IS NOT NULL);


CREATE UNIQUE INDEX translationimportqueueentry__status__dateimported__id__idx ON public.translationimportqueueentry USING btree (status, dateimported, id);


CREATE INDEX translationmessage__msgstr0__idx ON public.translationmessage USING btree (msgstr0);


CREATE INDEX translationmessage__msgstr1__idx ON public.translationmessage USING btree (msgstr1) WHERE (msgstr1 IS NOT NULL);


CREATE INDEX translationmessage__msgstr2__idx ON public.translationmessage USING btree (msgstr2) WHERE (msgstr2 IS NOT NULL);


CREATE INDEX translationmessage__msgstr3__idx ON public.translationmessage USING btree (msgstr3) WHERE (msgstr3 IS NOT NULL);


CREATE INDEX translationmessage__msgstr4__idx ON public.translationmessage USING btree (msgstr4) WHERE (msgstr4 IS NOT NULL);


CREATE INDEX translationmessage__msgstr5__idx ON public.translationmessage USING btree (msgstr5) WHERE (msgstr5 IS NOT NULL);


CREATE INDEX translationmessage__potemplate__idx ON public.translationmessage USING btree (potemplate) WHERE (potemplate IS NOT NULL);


CREATE INDEX translationmessage__potmsgset__idx ON public.translationmessage USING btree (potmsgset);


CREATE INDEX translationmessage__potmsgset__language__idx ON public.translationmessage USING btree (potmsgset, language);


CREATE INDEX translationmessage__reviewer__idx ON public.translationmessage USING btree (reviewer);


CREATE INDEX translationmessage__submitter__idx ON public.translationmessage USING btree (submitter);


CREATE UNIQUE INDEX translationtemplateitem__potemplate__potmsgset__key ON public.translationtemplateitem USING btree (potemplate, potmsgset);


CREATE INDEX translationtemplateitem__potemplate__sequence__idx ON public.translationtemplateitem USING btree (potemplate, sequence);


CREATE UNIQUE INDEX translationtemplateitem__potemplate__sequence__key ON public.translationtemplateitem USING btree (potemplate, sequence) WHERE (sequence > 0);


CREATE INDEX translationtemplateitem__potmsgset__idx ON public.translationtemplateitem USING btree (potmsgset);


CREATE INDEX translationtemplatesbuild__branch__idx ON public.translationtemplatesbuild USING btree (branch);


CREATE INDEX translationtemplatesbuild__build_farm_job__idx ON public.translationtemplatesbuild USING btree (build_farm_job);


CREATE INDEX translationtemplatesbuild__log__idx ON public.translationtemplatesbuild USING btree (log);


CREATE INDEX translator__translator__idx ON public.translator USING btree (translator);


CREATE INDEX usertouseremail__recipient__idx ON public.usertouseremail USING btree (recipient);


CREATE INDEX usertouseremail__sender__date_sent__idx ON public.usertouseremail USING btree (sender, date_sent);


CREATE INDEX vote__person__idx ON public.vote USING btree (person);


CREATE INDEX votecast_poll_idx ON public.votecast USING btree (poll);


CREATE INDEX webhook__branch__id__idx ON public.webhook USING btree (branch, id) WHERE (branch IS NOT NULL);


CREATE INDEX webhook__git_repository__id__idx ON public.webhook USING btree (git_repository, id) WHERE (git_repository IS NOT NULL);


CREATE INDEX webhook__snap__id__idx ON public.webhook USING btree (snap, id) WHERE (snap IS NOT NULL);


CREATE INDEX webhookjob__webhook__job_type__job__idx ON public.webhookjob USING btree (webhook, job_type, job);


CREATE INDEX wikiname_person_idx ON public.wikiname USING btree (person);


CREATE INDEX xref__creator__idx ON public.xref USING btree (creator);


CREATE INDEX xref__from_type__to_type__idx ON public.xref USING btree (from_type, to_type);


CREATE UNIQUE INDEX xref__int__key ON public.xref USING btree (from_type, from_id_int, to_type, to_id_int);


CREATE UNIQUE INDEX xref__int_inverse__key ON public.xref USING btree (to_type, to_id_int, from_type, from_id_int);


CREATE UNIQUE INDEX xref__inverse__key ON public.xref USING btree (to_type, to_id, from_type, from_id);


CREATE INDEX xref__to_type__from_type__idx ON public.xref USING btree (to_type, from_type);


CREATE TRIGGER accessartifactgrant_denorm_to_artifacts_trigger AFTER INSERT OR DELETE OR UPDATE ON public.accessartifactgrant FOR EACH ROW EXECUTE PROCEDURE public.accessartifact_maintain_denorm_to_artifacts_trig();


CREATE TRIGGER accessartifactgrant_maintain_accesspolicygrantflat_trigger AFTER INSERT OR DELETE OR UPDATE ON public.accessartifactgrant FOR EACH ROW EXECUTE PROCEDURE public.accessartifactgrant_maintain_accesspolicygrantflat_trig();


CREATE TRIGGER accesspolicyartifact_denorm_to_artifacts_trigger AFTER INSERT OR DELETE OR UPDATE ON public.accesspolicyartifact FOR EACH ROW EXECUTE PROCEDURE public.accessartifact_maintain_denorm_to_artifacts_trig();


CREATE TRIGGER accesspolicyartifact_maintain_accesspolicyartifactflat_trigger AFTER INSERT OR DELETE OR UPDATE ON public.accesspolicyartifact FOR EACH ROW EXECUTE PROCEDURE public.accesspolicyartifact_maintain_accesspolicyartifactflat_trig();


CREATE TRIGGER accesspolicygrant_maintain_accesspolicygrantflat_trigger AFTER INSERT OR DELETE OR UPDATE ON public.accesspolicygrant FOR EACH ROW EXECUTE PROCEDURE public.accesspolicygrant_maintain_accesspolicygrantflat_trig();


CREATE TRIGGER branch_maintain_access_cache AFTER INSERT OR UPDATE OF information_type ON public.branch FOR EACH ROW EXECUTE PROCEDURE public.branch_maintain_access_cache_trig();


CREATE TRIGGER bug_latest_patch_uploaded_on_delete_t AFTER DELETE ON public.bugattachment FOR EACH ROW EXECUTE PROCEDURE public.bug_update_latest_patch_uploaded_on_delete();


CREATE TRIGGER bug_latest_patch_uploaded_on_insert_update_t AFTER INSERT OR UPDATE ON public.bugattachment FOR EACH ROW EXECUTE PROCEDURE public.bug_update_latest_patch_uploaded_on_insert_update();


CREATE TRIGGER bugmessage__owner__mirror AFTER INSERT OR UPDATE ON public.bugmessage FOR EACH ROW EXECUTE PROCEDURE public.bugmessage_copy_owner_from_message();


CREATE TRIGGER bugtag_maintain_bug_summary_after_trigger AFTER INSERT OR DELETE OR UPDATE ON public.bugtag FOR EACH ROW EXECUTE PROCEDURE public.bugtag_maintain_bug_summary();


CREATE TRIGGER bugtag_maintain_bug_summary_before_trigger BEFORE INSERT OR DELETE OR UPDATE ON public.bugtag FOR EACH ROW EXECUTE PROCEDURE public.bugtag_maintain_bug_summary();


CREATE TRIGGER bugtaskflat_maintain_bug_summary AFTER INSERT OR DELETE OR UPDATE ON public.bugtaskflat FOR EACH ROW EXECUTE PROCEDURE public.bugtaskflat_maintain_bug_summary();


CREATE TRIGGER gitrepository_maintain_access_cache AFTER INSERT OR UPDATE OF information_type ON public.gitrepository FOR EACH ROW EXECUTE PROCEDURE public.gitrepository_maintain_access_cache_trig();


CREATE TRIGGER lp_mirror_openididentifier_del_t AFTER DELETE ON public.openididentifier FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_openididentifier_del();


CREATE TRIGGER lp_mirror_openididentifier_ins_t AFTER INSERT ON public.openididentifier FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_openididentifier_ins();


CREATE TRIGGER lp_mirror_openididentifier_upd_t AFTER UPDATE ON public.openididentifier FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_openididentifier_upd();


CREATE TRIGGER lp_mirror_person_del_t AFTER DELETE ON public.person FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_del();


CREATE TRIGGER lp_mirror_person_ins_t AFTER INSERT ON public.person FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_person_ins();


CREATE TRIGGER lp_mirror_person_upd_t AFTER UPDATE ON public.person FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_person_upd();


CREATE TRIGGER lp_mirror_personlocation_del_t AFTER DELETE ON public.teamparticipation FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_del();


CREATE TRIGGER lp_mirror_personlocation_ins_t AFTER INSERT ON public.personlocation FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_personlocation_ins();


CREATE TRIGGER lp_mirror_personlocation_upd_t AFTER UPDATE ON public.personlocation FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_personlocation_upd();


CREATE TRIGGER lp_mirror_teamparticipation_del_t AFTER DELETE ON public.teamparticipation FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_del();


CREATE TRIGGER lp_mirror_teamparticipation_ins_t AFTER INSERT ON public.teamparticipation FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_teamparticipation_ins();


CREATE TRIGGER lp_mirror_teamparticipation_upd_t AFTER UPDATE ON public.teamparticipation FOR EACH ROW EXECUTE PROCEDURE public.lp_mirror_teamparticipation_upd();


CREATE TRIGGER message__owner__mirror AFTER UPDATE ON public.message FOR EACH ROW EXECUTE PROCEDURE public.message_copy_owner_to_bugmessage();


CREATE TRIGGER message__owner__mirror__questionmessage AFTER UPDATE ON public.message FOR EACH ROW EXECUTE PROCEDURE public.message_copy_owner_to_questionmessage();


CREATE TRIGGER mv_branch_distribution_update_t AFTER UPDATE ON public.distribution FOR EACH ROW EXECUTE PROCEDURE public.mv_branch_distribution_update();


CREATE TRIGGER mv_branch_distroseries_update_t AFTER UPDATE ON public.distroseries FOR EACH ROW EXECUTE PROCEDURE public.mv_branch_distroseries_update();


CREATE TRIGGER mv_branch_person_update_t AFTER UPDATE ON public.person FOR EACH ROW EXECUTE PROCEDURE public.mv_branch_person_update();


CREATE TRIGGER mv_branch_product_update_t AFTER UPDATE ON public.product FOR EACH ROW EXECUTE PROCEDURE public.mv_branch_product_update();


CREATE TRIGGER mv_pillarname_distribution_t AFTER INSERT OR UPDATE ON public.distribution FOR EACH ROW EXECUTE PROCEDURE public.mv_pillarname_distribution();


CREATE TRIGGER mv_pillarname_product_t AFTER INSERT OR UPDATE ON public.product FOR EACH ROW EXECUTE PROCEDURE public.mv_pillarname_product();


CREATE TRIGGER mv_pillarname_project_t AFTER INSERT OR UPDATE ON public.project FOR EACH ROW EXECUTE PROCEDURE public.mv_pillarname_project();


CREATE TRIGGER mv_pofiletranslator_translationmessage AFTER INSERT OR UPDATE ON public.translationmessage FOR EACH ROW EXECUTE PROCEDURE public.mv_pofiletranslator_translationmessage();


CREATE TRIGGER packageset_deleted_trig BEFORE DELETE ON public.packageset FOR EACH ROW EXECUTE PROCEDURE public.packageset_deleted_trig();


CREATE TRIGGER packageset_inserted_trig AFTER INSERT ON public.packageset FOR EACH ROW EXECUTE PROCEDURE public.packageset_inserted_trig();


CREATE TRIGGER packagesetinclusion_deleted_trig BEFORE DELETE ON public.packagesetinclusion FOR EACH ROW EXECUTE PROCEDURE public.packagesetinclusion_deleted_trig();


CREATE TRIGGER packagesetinclusion_inserted_trig AFTER INSERT ON public.packagesetinclusion FOR EACH ROW EXECUTE PROCEDURE public.packagesetinclusion_inserted_trig();


CREATE TRIGGER questionmessage__owner__mirror AFTER INSERT OR UPDATE ON public.questionmessage FOR EACH ROW EXECUTE PROCEDURE public.questionmessage_copy_owner_from_message();


CREATE TRIGGER set_bug_message_count_t AFTER INSERT OR DELETE OR UPDATE ON public.bugmessage FOR EACH ROW EXECUTE PROCEDURE public.set_bug_message_count();


CREATE TRIGGER set_bug_number_of_duplicates_t AFTER INSERT OR DELETE OR UPDATE ON public.bug FOR EACH ROW EXECUTE PROCEDURE public.set_bug_number_of_duplicates();


CREATE TRIGGER set_bug_users_affected_count_t AFTER INSERT OR DELETE OR UPDATE ON public.bugaffectsperson FOR EACH ROW EXECUTE PROCEDURE public.set_bug_users_affected_count();


CREATE TRIGGER set_bugtask_date_milestone_set_t AFTER INSERT OR UPDATE ON public.bugtask FOR EACH ROW EXECUTE PROCEDURE public.set_bugtask_date_milestone_set();


CREATE TRIGGER set_date_last_message_t AFTER INSERT OR DELETE OR UPDATE ON public.bugmessage FOR EACH ROW EXECUTE PROCEDURE public.set_bug_date_last_message();


CREATE TRIGGER set_date_status_set_t BEFORE UPDATE ON public.account FOR EACH ROW EXECUTE PROCEDURE public.set_date_status_set();


CREATE TRIGGER specification_maintain_access_cache AFTER INSERT OR UPDATE OF information_type ON public.specification FOR EACH ROW EXECUTE PROCEDURE public.specification_maintain_access_cache_trig();


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.binarypackagerelease FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('summary', 'b', 'description', 'c');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.cve FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('sequence', 'a', 'description', 'b');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.distroseriespackagecache FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('name', 'a', 'summaries', 'b', 'descriptions', 'c');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.message FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('subject', 'b');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.messagechunk FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('content', 'c');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.product FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('name', 'a', 'displayname', 'a', 'title', 'b', 'summary', 'c', 'description', 'd');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.project FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('name', 'a', 'displayname', 'a', 'title', 'b', 'summary', 'c', 'description', 'd');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.question FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('title', 'a', 'description', 'b', 'whiteboard', 'b');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.bug FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('name', 'a', 'title', 'b', 'description', 'd');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.person FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('name', 'a', 'displayname', 'a');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.specification FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('name', 'a', 'title', 'a', 'summary', 'b', 'whiteboard', 'd');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.distribution FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('name', 'a', 'displayname', 'a', 'title', 'b', 'summary', 'c', 'description', 'd');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.productreleasefile FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('description', 'd');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.faq FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('title', 'a', 'tags', 'b', 'content', 'd');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.archive FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('description', 'a', 'package_description_cache', 'b');


CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON public.distributionsourcepackagecache FOR EACH ROW EXECUTE PROCEDURE public.ftiupdate('name', 'a', 'binpkgnames', 'b', 'binpkgsummaries', 'c', 'binpkgdescriptions', 'd');


CREATE TRIGGER update_branch_name_cache_t BEFORE INSERT OR UPDATE ON public.branch FOR EACH ROW EXECUTE PROCEDURE public.update_branch_name_cache();


CREATE TRIGGER you_are_your_own_member AFTER INSERT ON public.person FOR EACH ROW EXECUTE PROCEDURE public.you_are_your_own_member();


CREATE TRIGGER z_bug_maintain_bugtaskflat_trigger AFTER UPDATE ON public.bug FOR EACH ROW EXECUTE PROCEDURE public.bug_maintain_bugtaskflat_trig();


CREATE TRIGGER z_bugtask_maintain_bugtaskflat_trigger AFTER INSERT OR DELETE OR UPDATE ON public.bugtask FOR EACH ROW EXECUTE PROCEDURE public.bugtask_maintain_bugtaskflat_trig();


ALTER TABLE ONLY public.builder
    ADD CONSTRAINT "$1" FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT "$1" FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.productreleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (productrelease) REFERENCES public.productrelease(id);


ALTER TABLE ONLY public.spokenin
    ADD CONSTRAINT "$1" FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.bugsubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugactivity
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.sshkey
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.polloption
    ADD CONSTRAINT "$1" FOREIGN KEY (poll) REFERENCES public.poll(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT "$1" FOREIGN KEY (bug_supervisor) REFERENCES public.person(id);


ALTER TABLE ONLY public.country
    ADD CONSTRAINT "$1" FOREIGN KEY (continent) REFERENCES public.continent(id);


ALTER TABLE ONLY public.sourcepackagereleasefile
    ADD CONSTRAINT "$1" FOREIGN KEY (sourcepackagerelease) REFERENCES public.sourcepackagerelease(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.builder
    ADD CONSTRAINT "$2" FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.productreleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.sourcepackagereleasefile
    ADD CONSTRAINT "$2" FOREIGN KEY (libraryfile) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.spokenin
    ADD CONSTRAINT "$2" FOREIGN KEY (country) REFERENCES public.country(id);


ALTER TABLE ONLY public.bugsubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.buildqueue
    ADD CONSTRAINT "$2" FOREIGN KEY (builder) REFERENCES public.builder(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT "$2" FOREIGN KEY (members) REFERENCES public.person(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT "$3" FOREIGN KEY (bug_supervisor) REFERENCES public.person(id);


ALTER TABLE ONLY public.pofile
    ADD CONSTRAINT "$3" FOREIGN KEY (from_sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.accessartifact
    ADD CONSTRAINT accessartifact_bug_fkey FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.accessartifact
    ADD CONSTRAINT accessartifact_gitrepository_fkey FOREIGN KEY (gitrepository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.accessartifact
    ADD CONSTRAINT accessartifact_specification_fkey FOREIGN KEY (specification) REFERENCES public.specification(id);


ALTER TABLE ONLY public.accessartifactgrant
    ADD CONSTRAINT accessartifactgrant__grantee__fk FOREIGN KEY (grantee) REFERENCES public.person(id);


ALTER TABLE ONLY public.accessartifactgrant
    ADD CONSTRAINT accessartifactgrant__grantor__fk FOREIGN KEY (grantor) REFERENCES public.person(id);


ALTER TABLE ONLY public.accessartifactgrant
    ADD CONSTRAINT accessartifactgrant_artifact_fkey FOREIGN KEY (artifact) REFERENCES public.accessartifact(id);


ALTER TABLE ONLY public.accesspolicy
    ADD CONSTRAINT accesspolicy_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.accesspolicy
    ADD CONSTRAINT accesspolicy_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.accesspolicy
    ADD CONSTRAINT accesspolicy_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.accesspolicyartifact
    ADD CONSTRAINT accesspolicyartifact_artifact_fkey FOREIGN KEY (artifact) REFERENCES public.accessartifact(id);


ALTER TABLE ONLY public.accesspolicyartifact
    ADD CONSTRAINT accesspolicyartifact_policy_fkey FOREIGN KEY (policy) REFERENCES public.accesspolicy(id);


ALTER TABLE ONLY public.accesspolicygrant
    ADD CONSTRAINT accesspolicygrant__grantee__fk FOREIGN KEY (grantee) REFERENCES public.person(id);


ALTER TABLE ONLY public.accesspolicygrant
    ADD CONSTRAINT accesspolicygrant__grantor__fk FOREIGN KEY (grantor) REFERENCES public.person(id);


ALTER TABLE ONLY public.accesspolicygrant
    ADD CONSTRAINT accesspolicygrant_policy_fkey FOREIGN KEY (policy) REFERENCES public.accesspolicy(id);


ALTER TABLE ONLY public.accesspolicygrantflat
    ADD CONSTRAINT accesspolicygrantflat_artifact_fkey FOREIGN KEY (artifact) REFERENCES public.accessartifact(id);


ALTER TABLE ONLY public.accesspolicygrantflat
    ADD CONSTRAINT accesspolicygrantflat_policy_fkey FOREIGN KEY (policy) REFERENCES public.accesspolicy(id);


ALTER TABLE ONLY public.karma
    ADD CONSTRAINT action_fkey FOREIGN KEY (action) REFERENCES public.karmaaction(id);


ALTER TABLE ONLY public.announcement
    ADD CONSTRAINT announcement_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.announcement
    ADD CONSTRAINT announcement_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.announcement
    ADD CONSTRAINT announcement_project_fkey FOREIGN KEY (project) REFERENCES public.project(id);


ALTER TABLE ONLY public.announcement
    ADD CONSTRAINT announcement_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.answercontact
    ADD CONSTRAINT answercontact__distribution__fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.answercontact
    ADD CONSTRAINT answercontact__person__fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.answercontact
    ADD CONSTRAINT answercontact__product__fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.answercontact
    ADD CONSTRAINT answercontact__sourcepackagename__fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.apportjob
    ADD CONSTRAINT apportjob_blob_fkey FOREIGN KEY (blob) REFERENCES public.temporaryblobstorage(id);


ALTER TABLE ONLY public.apportjob
    ADD CONSTRAINT apportjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id);


ALTER TABLE ONLY public.archive
    ADD CONSTRAINT archive__distribution__fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.archive
    ADD CONSTRAINT archive__owner__fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.archive
    ADD CONSTRAINT archive_signing_key_fkey FOREIGN KEY (signing_key) REFERENCES public.gpgkey(id);


ALTER TABLE ONLY public.archive
    ADD CONSTRAINT archive_signing_key_owner_fkey FOREIGN KEY (signing_key_owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.archivearch
    ADD CONSTRAINT archivearch__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.archivearch
    ADD CONSTRAINT archivearch_processor_fkey FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.archiveauthtoken
    ADD CONSTRAINT archiveauthtoken__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.archiveauthtoken
    ADD CONSTRAINT archiveauthtoken_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.archivedependency
    ADD CONSTRAINT archivedependency__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.archivedependency
    ADD CONSTRAINT archivedependency__dependency__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.archivedependency
    ADD CONSTRAINT archivedependency_component_fkey FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.archivefile
    ADD CONSTRAINT archivefile_archive_fkey FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.archivefile
    ADD CONSTRAINT archivefile_library_file_fkey FOREIGN KEY (library_file) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.archivejob
    ADD CONSTRAINT archivejob__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.archivejob
    ADD CONSTRAINT archivejob__job__fk FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.archivepermission
    ADD CONSTRAINT archivepermission__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.archivepermission
    ADD CONSTRAINT archivepermission__component__fk FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.archivepermission
    ADD CONSTRAINT archivepermission__packageset__fk FOREIGN KEY (packageset) REFERENCES public.packageset(id);


ALTER TABLE ONLY public.archivepermission
    ADD CONSTRAINT archivepermission__person__fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.archivepermission
    ADD CONSTRAINT archivepermission__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.archivesubscriber
    ADD CONSTRAINT archivesubscriber__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.archivesubscriber
    ADD CONSTRAINT archivesubscriber_cancelled_by_fkey FOREIGN KEY (cancelled_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.archivesubscriber
    ADD CONSTRAINT archivesubscriber_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.archivesubscriber
    ADD CONSTRAINT archivesubscriber_subscriber_fkey FOREIGN KEY (subscriber) REFERENCES public.person(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild__distro_arch_series__fk FOREIGN KEY (distro_arch_series) REFERENCES public.distroarchseries(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild__source_package_release__fk FOREIGN KEY (source_package_release) REFERENCES public.sourcepackagerelease(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_archive_fkey FOREIGN KEY (archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_build_farm_job_fkey FOREIGN KEY (build_farm_job) REFERENCES public.buildfarmjob(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_builder_fkey FOREIGN KEY (builder) REFERENCES public.builder(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_buildinfo_fkey FOREIGN KEY (buildinfo) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_distro_series_fkey FOREIGN KEY (distro_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_log_fkey FOREIGN KEY (log) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_processor_fkey FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_source_package_name_fkey FOREIGN KEY (source_package_name) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.binarypackagebuild
    ADD CONSTRAINT binarypackagebuild_upload_log_fkey FOREIGN KEY (upload_log) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.binarypackagefile
    ADD CONSTRAINT binarypackagefile_binarypackagerelease_fk FOREIGN KEY (binarypackagerelease) REFERENCES public.binarypackagerelease(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.binarypackagefile
    ADD CONSTRAINT binarypackagefile_libraryfile_fk FOREIGN KEY (libraryfile) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.binarypackagepublishinghistory
    ADD CONSTRAINT binarypackagepublishinghistory_binarypackagename_fkey FOREIGN KEY (binarypackagename) REFERENCES public.binarypackagename(id);


ALTER TABLE ONLY public.binarypackagepublishinghistory
    ADD CONSTRAINT binarypackagepublishinghistory_supersededby_fk FOREIGN KEY (supersededby) REFERENCES public.binarypackagebuild(id);


ALTER TABLE ONLY public.binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES public.binarypackagename(id);


ALTER TABLE ONLY public.binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_build_fk FOREIGN KEY (build) REFERENCES public.binarypackagebuild(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_component_fk FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_debug_package_fkey FOREIGN KEY (debug_package) REFERENCES public.binarypackagerelease(id);


ALTER TABLE ONLY public.binarypackagerelease
    ADD CONSTRAINT binarypackagerelease_section_fk FOREIGN KEY (section) REFERENCES public.section(id);


ALTER TABLE ONLY public.binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount_archive_fkey FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount_binary_package_release_fkey FOREIGN KEY (binary_package_release) REFERENCES public.binarypackagerelease(id);


ALTER TABLE ONLY public.binarypackagereleasedownloadcount
    ADD CONSTRAINT binarypackagereleasedownloadcount_country_fkey FOREIGN KEY (country) REFERENCES public.country(id);


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.incrementaldiff
    ADD CONSTRAINT branch_merge_proposal_fk FOREIGN KEY (branch_merge_proposal) REFERENCES public.branchmergeproposal(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch_product_fk FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES public.person(id);


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.branch
    ADD CONSTRAINT branch_stacked_on_fkey FOREIGN KEY (stacked_on) REFERENCES public.branch(id);


ALTER TABLE ONLY public.branchjob
    ADD CONSTRAINT branchjob_branch_fkey FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.branchjob
    ADD CONSTRAINT branchjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_dependent_branch_fkey FOREIGN KEY (dependent_branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_dependent_git_repository_fkey FOREIGN KEY (dependent_git_repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_merge_log_file_fkey FOREIGN KEY (merge_log_file) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_merge_reporter_fkey FOREIGN KEY (merge_reporter) REFERENCES public.person(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_merger_fkey FOREIGN KEY (merger) REFERENCES public.person(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_queuer_fkey FOREIGN KEY (queuer) REFERENCES public.person(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES public.person(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_source_branch_fkey FOREIGN KEY (source_branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_source_git_repository_fkey FOREIGN KEY (source_git_repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_superseded_by_fkey FOREIGN KEY (superseded_by) REFERENCES public.branchmergeproposal(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_target_branch_fkey FOREIGN KEY (target_branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.branchmergeproposal
    ADD CONSTRAINT branchmergeproposal_target_git_repository_fkey FOREIGN KEY (target_git_repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.branchmergeproposaljob
    ADD CONSTRAINT branchmergeproposaljob_branch_merge_proposal_fkey FOREIGN KEY (branch_merge_proposal) REFERENCES public.branchmergeproposal(id);


ALTER TABLE ONLY public.branchmergeproposaljob
    ADD CONSTRAINT branchmergeproposaljob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.branchrevision
    ADD CONSTRAINT branchrevision__branch__fk FOREIGN KEY (branch) REFERENCES public.branch(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.branchrevision
    ADD CONSTRAINT branchrevision__revision__fk FOREIGN KEY (revision) REFERENCES public.revision(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;


ALTER TABLE ONLY public.branchsubscription
    ADD CONSTRAINT branchsubscription_branch_fk FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.branchsubscription
    ADD CONSTRAINT branchsubscription_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.branchsubscription
    ADD CONSTRAINT branchsubscription_subscribed_by_fkey FOREIGN KEY (subscribed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.bug
    ADD CONSTRAINT bug__who_made_private__fk FOREIGN KEY (who_made_private) REFERENCES public.person(id);


ALTER TABLE ONLY public.bug
    ADD CONSTRAINT bug_duplicateof_fk FOREIGN KEY (duplicateof) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bug
    ADD CONSTRAINT bug_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugactivity
    ADD CONSTRAINT bugactivity__person__fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugaffectsperson
    ADD CONSTRAINT bugaffectsperson_bug_fkey FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugaffectsperson
    ADD CONSTRAINT bugaffectsperson_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugattachment
    ADD CONSTRAINT bugattachment_bug_fk FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugattachment
    ADD CONSTRAINT bugattachment_libraryfile_fk FOREIGN KEY (libraryfile) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.bugattachment
    ADD CONSTRAINT bugattachment_message_fk FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.bugbranch
    ADD CONSTRAINT bugbranch_branch_fkey FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.bugbranch
    ADD CONSTRAINT bugbranch_bug_fkey FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugbranch
    ADD CONSTRAINT bugbranch_fixed_in_revision_fkey FOREIGN KEY (revision_hint) REFERENCES public.revision(id);


ALTER TABLE ONLY public.bugbranch
    ADD CONSTRAINT bugbranch_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugmessage
    ADD CONSTRAINT bugmessage__bug__fk FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugmessage
    ADD CONSTRAINT bugmessage_bugwatch_fkey FOREIGN KEY (bugwatch) REFERENCES public.bugwatch(id);


ALTER TABLE ONLY public.bugmessage
    ADD CONSTRAINT bugmessage_message_fk FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.bugmute
    ADD CONSTRAINT bugmute_bug_fkey FOREIGN KEY (bug) REFERENCES public.bug(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugmute
    ADD CONSTRAINT bugmute_person_fkey FOREIGN KEY (person) REFERENCES public.person(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugnomination
    ADD CONSTRAINT bugnomination__bug__fk FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugnomination
    ADD CONSTRAINT bugnomination__decider__fk FOREIGN KEY (decider) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugnomination
    ADD CONSTRAINT bugnomination__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.bugnomination
    ADD CONSTRAINT bugnomination__owner__fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugnomination
    ADD CONSTRAINT bugnomination__productseries__fk FOREIGN KEY (productseries) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.bugnotification
    ADD CONSTRAINT bugnotification_activity_fkey FOREIGN KEY (activity) REFERENCES public.bugactivity(id);


ALTER TABLE ONLY public.bugnotification
    ADD CONSTRAINT bugnotification_bug_fkey FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugnotification
    ADD CONSTRAINT bugnotification_message_fkey FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.bugnotificationarchive
    ADD CONSTRAINT bugnotificationarchive__bug__fk FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugnotificationarchive
    ADD CONSTRAINT bugnotificationarchive__message__fk FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.bugnotificationattachment
    ADD CONSTRAINT bugnotificationattachment__bug_notification__fk FOREIGN KEY (bug_notification) REFERENCES public.bugnotification(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugnotificationattachment
    ADD CONSTRAINT bugnotificationattachment_message_fkey FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.bugnotificationfilter
    ADD CONSTRAINT bugnotificationfilter_bug_notification_fkey FOREIGN KEY (bug_notification) REFERENCES public.bugnotification(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugnotificationfilter
    ADD CONSTRAINT bugnotificationfilter_bug_subscription_filter_fkey FOREIGN KEY (bug_subscription_filter) REFERENCES public.bugsubscriptionfilter(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugnotificationrecipient
    ADD CONSTRAINT bugnotificationrecipient__bug_notification__fk FOREIGN KEY (bug_notification) REFERENCES public.bugnotification(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugnotificationrecipient
    ADD CONSTRAINT bugnotificationrecipient_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugsubscription
    ADD CONSTRAINT bugsubscription_subscribed_by_fkey FOREIGN KEY (subscribed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugsubscriptionfilter
    ADD CONSTRAINT bugsubscriptionfilter__structuralsubscription__fk FOREIGN KEY (structuralsubscription) REFERENCES public.structuralsubscription(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugsubscriptionfilterimportance
    ADD CONSTRAINT bugsubscriptionfilterimportance_filter_fkey FOREIGN KEY (filter) REFERENCES public.bugsubscriptionfilter(id);


ALTER TABLE ONLY public.bugsubscriptionfilterinformationtype
    ADD CONSTRAINT bugsubscriptionfilterinformationtype_filter_fkey FOREIGN KEY (filter) REFERENCES public.bugsubscriptionfilter(id);


ALTER TABLE ONLY public.bugsubscriptionfiltermute
    ADD CONSTRAINT bugsubscriptionfiltermute_filter_fkey FOREIGN KEY (filter) REFERENCES public.bugsubscriptionfilter(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugsubscriptionfiltermute
    ADD CONSTRAINT bugsubscriptionfiltermute_person_fkey FOREIGN KEY (person) REFERENCES public.person(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugsubscriptionfilterstatus
    ADD CONSTRAINT bugsubscriptionfilterstatus_filter_fkey FOREIGN KEY (filter) REFERENCES public.bugsubscriptionfilter(id);


ALTER TABLE ONLY public.bugsubscriptionfiltertag
    ADD CONSTRAINT bugsubscriptionfiltertag_filter_fkey FOREIGN KEY (filter) REFERENCES public.bugsubscriptionfilter(id);


ALTER TABLE ONLY public.bugsummary
    ADD CONSTRAINT bugsummary_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugsummary
    ADD CONSTRAINT bugsummary_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES public.distroseries(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugsummary
    ADD CONSTRAINT bugsummary_milestone_fkey FOREIGN KEY (milestone) REFERENCES public.milestone(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugsummary
    ADD CONSTRAINT bugsummary_product_fkey FOREIGN KEY (product) REFERENCES public.product(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugsummary
    ADD CONSTRAINT bugsummary_productseries_fkey FOREIGN KEY (productseries) REFERENCES public.productseries(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugsummary
    ADD CONSTRAINT bugsummary_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugsummary
    ADD CONSTRAINT bugsummaryjournal_viewed_by_fkey FOREIGN KEY (viewed_by) REFERENCES public.person(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.bugtag
    ADD CONSTRAINT bugtag__bug__fk FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__assignee__fk FOREIGN KEY (assignee) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__bug__fk FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__bugwatch__fk FOREIGN KEY (bugwatch) REFERENCES public.bugwatch(id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__distribution__fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__distribution__milestone__fk FOREIGN KEY (distribution, milestone) REFERENCES public.milestone(distribution, id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__owner__fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__product__fk FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__product__milestone__fk FOREIGN KEY (product, milestone) REFERENCES public.milestone(product, id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__productseries__fk FOREIGN KEY (productseries) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.bugtask
    ADD CONSTRAINT bugtask__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.bugtracker
    ADD CONSTRAINT bugtracker_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugtrackeralias
    ADD CONSTRAINT bugtrackeralias__bugtracker__fk FOREIGN KEY (bugtracker) REFERENCES public.bugtracker(id);


ALTER TABLE ONLY public.bugtrackercomponent
    ADD CONSTRAINT bugtrackercomponent_component_group_fkey FOREIGN KEY (component_group) REFERENCES public.bugtrackercomponentgroup(id);


ALTER TABLE ONLY public.bugtrackercomponent
    ADD CONSTRAINT bugtrackercomponent_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.bugtrackercomponent
    ADD CONSTRAINT bugtrackercomponent_source_package_name_fkey FOREIGN KEY (source_package_name) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.bugtrackercomponentgroup
    ADD CONSTRAINT bugtrackercomponentgroup_bug_tracker_fkey FOREIGN KEY (bug_tracker) REFERENCES public.bugtracker(id);


ALTER TABLE ONLY public.bugtrackerperson
    ADD CONSTRAINT bugtrackerperson_bugtracker_fkey FOREIGN KEY (bugtracker) REFERENCES public.bugtracker(id);


ALTER TABLE ONLY public.bugtrackerperson
    ADD CONSTRAINT bugtrackerperson_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugwatch
    ADD CONSTRAINT bugwatch_bug_fk FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.bugwatch
    ADD CONSTRAINT bugwatch_bugtracker_fk FOREIGN KEY (bugtracker) REFERENCES public.bugtracker(id);


ALTER TABLE ONLY public.bugwatch
    ADD CONSTRAINT bugwatch_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.bugwatchactivity
    ADD CONSTRAINT bugwatchactivity_bug_watch_fkey FOREIGN KEY (bug_watch) REFERENCES public.bugwatch(id);


ALTER TABLE ONLY public.builderprocessor
    ADD CONSTRAINT builderprocessor_builder_fkey FOREIGN KEY (builder) REFERENCES public.builder(id);


ALTER TABLE ONLY public.builderprocessor
    ADD CONSTRAINT builderprocessor_processor_fkey FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.buildfarmjob
    ADD CONSTRAINT buildfarmjob__builder__fk FOREIGN KEY (builder) REFERENCES public.builder(id);


ALTER TABLE ONLY public.buildfarmjob
    ADD CONSTRAINT buildfarmjob_archive_fkey FOREIGN KEY (archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.buildqueue
    ADD CONSTRAINT buildqueue__build_farm_job__fk FOREIGN KEY (build_farm_job) REFERENCES public.buildfarmjob(id);


ALTER TABLE ONLY public.buildqueue
    ADD CONSTRAINT buildqueue__processor__fk FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.codeimport
    ADD CONSTRAINT codeimport_assignee_fkey FOREIGN KEY (assignee) REFERENCES public.person(id);


ALTER TABLE ONLY public.codeimport
    ADD CONSTRAINT codeimport_branch_fkey FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.codeimport
    ADD CONSTRAINT codeimport_git_repository_fkey FOREIGN KEY (git_repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.codeimport
    ADD CONSTRAINT codeimport_owner_fkey FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.codeimport
    ADD CONSTRAINT codeimport_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.codeimportevent
    ADD CONSTRAINT codeimportevent__code_import__fk FOREIGN KEY (code_import) REFERENCES public.codeimport(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.codeimportevent
    ADD CONSTRAINT codeimportevent__machine__fk FOREIGN KEY (machine) REFERENCES public.codeimportmachine(id);


ALTER TABLE ONLY public.codeimportevent
    ADD CONSTRAINT codeimportevent__person__fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.codeimporteventdata
    ADD CONSTRAINT codeimporteventdata__event__fk FOREIGN KEY (event) REFERENCES public.codeimportevent(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.codeimportjob
    ADD CONSTRAINT codeimportjob__code_import__fk FOREIGN KEY (code_import) REFERENCES public.codeimport(id);


ALTER TABLE ONLY public.codeimportjob
    ADD CONSTRAINT codeimportjob__machine__fk FOREIGN KEY (machine) REFERENCES public.codeimportmachine(id);


ALTER TABLE ONLY public.codeimportjob
    ADD CONSTRAINT codeimportjob__requesting_user__fk FOREIGN KEY (requesting_user) REFERENCES public.person(id);


ALTER TABLE ONLY public.codeimportresult
    ADD CONSTRAINT codeimportresult__code_import__fk FOREIGN KEY (code_import) REFERENCES public.codeimport(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.codeimportresult
    ADD CONSTRAINT codeimportresult__log_file__fk FOREIGN KEY (log_file) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.codeimportresult
    ADD CONSTRAINT codeimportresult__machine__fk FOREIGN KEY (machine) REFERENCES public.codeimportmachine(id);


ALTER TABLE ONLY public.codeimportresult
    ADD CONSTRAINT codeimportresult__requesting_user__fk FOREIGN KEY (requesting_user) REFERENCES public.person(id);


ALTER TABLE ONLY public.codereviewinlinecomment
    ADD CONSTRAINT codereviewinlinecomment_comment_fkey FOREIGN KEY (comment) REFERENCES public.codereviewmessage(id);


ALTER TABLE ONLY public.codereviewinlinecomment
    ADD CONSTRAINT codereviewinlinecomment_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.codereviewinlinecomment
    ADD CONSTRAINT codereviewinlinecomment_previewdiff_fkey FOREIGN KEY (previewdiff) REFERENCES public.previewdiff(id);


ALTER TABLE ONLY public.codereviewinlinecommentdraft
    ADD CONSTRAINT codereviewinlinecommentdraft_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.codereviewinlinecommentdraft
    ADD CONSTRAINT codereviewinlinecommentdraft_previewdiff_fkey FOREIGN KEY (previewdiff) REFERENCES public.previewdiff(id);


ALTER TABLE ONLY public.codereviewmessage
    ADD CONSTRAINT codereviewmessage_branch_merge_proposal_fkey FOREIGN KEY (branch_merge_proposal) REFERENCES public.branchmergeproposal(id);


ALTER TABLE ONLY public.codereviewmessage
    ADD CONSTRAINT codereviewmessage_message_fkey FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.codereviewvote
    ADD CONSTRAINT codereviewvote_branch_merge_proposal_fkey FOREIGN KEY (branch_merge_proposal) REFERENCES public.branchmergeproposal(id);


ALTER TABLE ONLY public.codereviewvote
    ADD CONSTRAINT codereviewvote_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.codereviewvote
    ADD CONSTRAINT codereviewvote_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES public.person(id);


ALTER TABLE ONLY public.codereviewvote
    ADD CONSTRAINT codereviewvote_vote_message_fkey FOREIGN KEY (vote_message) REFERENCES public.codereviewmessage(id);


ALTER TABLE ONLY public.commercialsubscription
    ADD CONSTRAINT commercialsubscription__product__fk FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.commercialsubscription
    ADD CONSTRAINT commercialsubscription__purchaser__fk FOREIGN KEY (purchaser) REFERENCES public.person(id);


ALTER TABLE ONLY public.commercialsubscription
    ADD CONSTRAINT commercialsubscription__registrant__fk FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.componentselection
    ADD CONSTRAINT componentselection__component__fk FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.componentselection
    ADD CONSTRAINT componentselection__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT creator_fkey FOREIGN KEY (creator) REFERENCES public.person(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.customlanguagecode
    ADD CONSTRAINT customlanguagecode_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.customlanguagecode
    ADD CONSTRAINT customlanguagecode_language_fkey FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.customlanguagecode
    ADD CONSTRAINT customlanguagecode_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.customlanguagecode
    ADD CONSTRAINT customlanguagecode_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.cvereference
    ADD CONSTRAINT cvereference_cve_fk FOREIGN KEY (cve) REFERENCES public.cve(id);


ALTER TABLE ONLY public.diff
    ADD CONSTRAINT diff_diff_text_fkey FOREIGN KEY (diff_text) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.incrementaldiff
    ADD CONSTRAINT diff_fk FOREIGN KEY (diff) REFERENCES public.diff(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution__icon__fk FOREIGN KEY (icon) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution__logo__fk FOREIGN KEY (logo) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution__mugshot__fk FOREIGN KEY (mugshot) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution_driver_fk FOREIGN KEY (driver) REFERENCES public.person(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution_language_pack_admin_fkey FOREIGN KEY (language_pack_admin) REFERENCES public.person(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution_mirror_admin_fkey FOREIGN KEY (mirror_admin) REFERENCES public.person(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution_translation_focus_fkey FOREIGN KEY (translation_focus) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distribution
    ADD CONSTRAINT distribution_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES public.translationgroup(id);


ALTER TABLE ONLY public.distributionjob
    ADD CONSTRAINT distributionjob__job__fk FOREIGN KEY (job) REFERENCES public.job(id);


ALTER TABLE ONLY public.distributionjob
    ADD CONSTRAINT distributionjob_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.distributionjob
    ADD CONSTRAINT distributionjob_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distributionmirror
    ADD CONSTRAINT distributionmirror_country_fkey FOREIGN KEY (country) REFERENCES public.country(id);


ALTER TABLE ONLY public.distributionmirror
    ADD CONSTRAINT distributionmirror_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.distributionmirror
    ADD CONSTRAINT distributionmirror_owner_fkey FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.distributionmirror
    ADD CONSTRAINT distributionmirror_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES public.person(id);


ALTER TABLE ONLY public.distributionsourcepackage
    ADD CONSTRAINT distributionpackage__distribution__fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.distributionsourcepackage
    ADD CONSTRAINT distributionpackage__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_distribution_fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.distributionsourcepackagecache
    ADD CONSTRAINT distributionsourcepackagecache_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.distroarchseries
    ADD CONSTRAINT distroarchseries__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroarchseries
    ADD CONSTRAINT distroarchseries__owner__fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.distroarchseries
    ADD CONSTRAINT distroarchseries_processor_fkey FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distrorelease_parentrelease_fk FOREIGN KEY (parent_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroserieslanguage
    ADD CONSTRAINT distroreleaselanguage_language_fk FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distroseries__distribution__fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distroseries__driver__fk FOREIGN KEY (driver) REFERENCES public.person(id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distroseries__language_pack_base__fk FOREIGN KEY (language_pack_base) REFERENCES public.languagepack(id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distroseries__language_pack_delta__fk FOREIGN KEY (language_pack_delta) REFERENCES public.languagepack(id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distroseries__language_pack_proposed__fk FOREIGN KEY (language_pack_proposed) REFERENCES public.languagepack(id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distroseries__nominatedarchindep__fk FOREIGN KEY (nominatedarchindep) REFERENCES public.distroarchseries(id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distroseries__parent_series__fk FOREIGN KEY (parent_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroseries
    ADD CONSTRAINT distroseries__registrant__fk FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.packagingjob
    ADD CONSTRAINT distroseries_fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroseriesdifference
    ADD CONSTRAINT distroseriesdifference__derived_series__fk FOREIGN KEY (derived_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroseriesdifference
    ADD CONSTRAINT distroseriesdifference__package_diff__fk FOREIGN KEY (package_diff) REFERENCES public.packagediff(id);


ALTER TABLE ONLY public.distroseriesdifference
    ADD CONSTRAINT distroseriesdifference__parent_package_diff__fk FOREIGN KEY (parent_package_diff) REFERENCES public.packagediff(id);


ALTER TABLE ONLY public.distroseriesdifference
    ADD CONSTRAINT distroseriesdifference__parentseries__fk FOREIGN KEY (parent_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroseriesdifference
    ADD CONSTRAINT distroseriesdifference__source_package_name__fk FOREIGN KEY (source_package_name) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.distroseriesdifferencemessage
    ADD CONSTRAINT distroseriesdifferencemessage__distro_series_difference__fk FOREIGN KEY (distro_series_difference) REFERENCES public.distroseriesdifference(id);


ALTER TABLE ONLY public.distroseriesdifferencemessage
    ADD CONSTRAINT distroseriesdifferencemessage__message__fk FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.distroserieslanguage
    ADD CONSTRAINT distroserieslanguage__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroserieslanguage
    ADD CONSTRAINT distroserieslanguage__language__fk FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.distroseriespackagecache
    ADD CONSTRAINT distroseriespackagecache__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.distroseriespackagecache
    ADD CONSTRAINT distroseriespackagecache__binarypackagename__fk FOREIGN KEY (binarypackagename) REFERENCES public.binarypackagename(id);


ALTER TABLE ONLY public.distroseriespackagecache
    ADD CONSTRAINT distroseriespackagecache__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroseriesparent
    ADD CONSTRAINT distroseriesparent__derivedseries__fk FOREIGN KEY (derived_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroseriesparent
    ADD CONSTRAINT distroseriesparent__parentseries__fk FOREIGN KEY (parent_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.distroseriesparent
    ADD CONSTRAINT distroseriesparent_component_fkey FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.emailaddress
    ADD CONSTRAINT emailaddress__person__fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.faq
    ADD CONSTRAINT faq_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.faq
    ADD CONSTRAINT faq_last_updated_by_fkey FOREIGN KEY (last_updated_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.faq
    ADD CONSTRAINT faq_owner_fkey FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.faq
    ADD CONSTRAINT faq_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.featuredproject
    ADD CONSTRAINT featuredproject_pillar_name_fkey FOREIGN KEY (pillar_name) REFERENCES public.pillarname(id);


ALTER TABLE ONLY public.featureflagchangelogentry
    ADD CONSTRAINT featureflagchangelogentry_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.flatpackagesetinclusion
    ADD CONSTRAINT flatpackagesetinclusion__child__fk FOREIGN KEY (child) REFERENCES public.packageset(id);


ALTER TABLE ONLY public.flatpackagesetinclusion
    ADD CONSTRAINT flatpackagesetinclusion__parent__fk FOREIGN KEY (parent) REFERENCES public.packageset(id);


ALTER TABLE ONLY public.gitactivity
    ADD CONSTRAINT gitactivity_changee_fkey FOREIGN KEY (changee) REFERENCES public.person(id);


ALTER TABLE ONLY public.gitactivity
    ADD CONSTRAINT gitactivity_changer_fkey FOREIGN KEY (changer) REFERENCES public.person(id);


ALTER TABLE ONLY public.gitactivity
    ADD CONSTRAINT gitactivity_repository_fkey FOREIGN KEY (repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.gitjob
    ADD CONSTRAINT gitjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.gitjob
    ADD CONSTRAINT gitjob_repository_fkey FOREIGN KEY (repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.gitref
    ADD CONSTRAINT gitref_author_fkey FOREIGN KEY (author) REFERENCES public.revisionauthor(id);


ALTER TABLE ONLY public.gitref
    ADD CONSTRAINT gitref_committer_fkey FOREIGN KEY (committer) REFERENCES public.revisionauthor(id);


ALTER TABLE ONLY public.gitref
    ADD CONSTRAINT gitref_repository_fkey FOREIGN KEY (repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.gitrepository
    ADD CONSTRAINT gitrepository_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.gitrepository
    ADD CONSTRAINT gitrepository_owner_fkey FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.gitrepository
    ADD CONSTRAINT gitrepository_project_fkey FOREIGN KEY (project) REFERENCES public.product(id);


ALTER TABLE ONLY public.gitrepository
    ADD CONSTRAINT gitrepository_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.gitrepository
    ADD CONSTRAINT gitrepository_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES public.person(id);


ALTER TABLE ONLY public.gitrepository
    ADD CONSTRAINT gitrepository_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.gitrule
    ADD CONSTRAINT gitrule_creator_fkey FOREIGN KEY (creator) REFERENCES public.person(id);


ALTER TABLE ONLY public.gitrule
    ADD CONSTRAINT gitrule_repository_fkey FOREIGN KEY (repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.gitrulegrant
    ADD CONSTRAINT gitrulegrant_grantee_fkey FOREIGN KEY (grantee) REFERENCES public.person(id);


ALTER TABLE ONLY public.gitrulegrant
    ADD CONSTRAINT gitrulegrant_grantor_fkey FOREIGN KEY (grantor) REFERENCES public.person(id);


ALTER TABLE ONLY public.gitrulegrant
    ADD CONSTRAINT gitrulegrant_repository_fkey FOREIGN KEY (repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.gitrulegrant
    ADD CONSTRAINT gitrulegrant_rule_fkey FOREIGN KEY (rule) REFERENCES public.gitrule(id);


ALTER TABLE ONLY public.gitsubscription
    ADD CONSTRAINT gitsubscription_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.gitsubscription
    ADD CONSTRAINT gitsubscription_repository_fkey FOREIGN KEY (repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.gitsubscription
    ADD CONSTRAINT gitsubscription_subscribed_by_fkey FOREIGN KEY (subscribed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.gpgkey
    ADD CONSTRAINT gpgkey_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.hwdevice
    ADD CONSTRAINT hwdevice_bus_vendor_id_fkey FOREIGN KEY (bus_vendor_id) REFERENCES public.hwvendorid(id);


ALTER TABLE ONLY public.hwdeviceclass
    ADD CONSTRAINT hwdeviceclass_device_fkey FOREIGN KEY (device) REFERENCES public.hwdevice(id);


ALTER TABLE ONLY public.hwdevicedriverlink
    ADD CONSTRAINT hwdevicedriverlink_device_fkey FOREIGN KEY (device) REFERENCES public.hwdevice(id);


ALTER TABLE ONLY public.hwdevicedriverlink
    ADD CONSTRAINT hwdevicedriverlink_driver_fkey FOREIGN KEY (driver) REFERENCES public.hwdriver(id);


ALTER TABLE ONLY public.hwdevicenamevariant
    ADD CONSTRAINT hwdevicenamevariant_device_fkey FOREIGN KEY (device) REFERENCES public.hwdevice(id);


ALTER TABLE ONLY public.hwdevicenamevariant
    ADD CONSTRAINT hwdevicenamevariant_vendor_name_fkey FOREIGN KEY (vendor_name) REFERENCES public.hwvendorname(id);


ALTER TABLE ONLY public.hwdmihandle
    ADD CONSTRAINT hwdmihandle_submission_fkey FOREIGN KEY (submission) REFERENCES public.hwsubmission(id);


ALTER TABLE ONLY public.hwdmivalue
    ADD CONSTRAINT hwdmivalue_handle_fkey FOREIGN KEY (handle) REFERENCES public.hwdmihandle(id);


ALTER TABLE ONLY public.hwsubmission
    ADD CONSTRAINT hwsubmission__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES public.distroarchseries(id);


ALTER TABLE ONLY public.hwsubmission
    ADD CONSTRAINT hwsubmission__owned__fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.hwsubmission
    ADD CONSTRAINT hwsubmission__raw_submission__fk FOREIGN KEY (raw_submission) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.hwsubmission
    ADD CONSTRAINT hwsubmission__system_fingerprint__fk FOREIGN KEY (system_fingerprint) REFERENCES public.hwsystemfingerprint(id);


ALTER TABLE ONLY public.hwsubmissionbug
    ADD CONSTRAINT hwsubmissionbug_bug_fkey FOREIGN KEY (bug) REFERENCES public.bug(id);


ALTER TABLE ONLY public.hwsubmissionbug
    ADD CONSTRAINT hwsubmissionbug_submission_fkey FOREIGN KEY (submission) REFERENCES public.hwsubmission(id);


ALTER TABLE ONLY public.hwsubmissiondevice
    ADD CONSTRAINT hwsubmissiondevice_device_driver_link_fkey FOREIGN KEY (device_driver_link) REFERENCES public.hwdevicedriverlink(id);


ALTER TABLE ONLY public.hwsubmissiondevice
    ADD CONSTRAINT hwsubmissiondevice_parent_fkey FOREIGN KEY (parent) REFERENCES public.hwsubmissiondevice(id);


ALTER TABLE ONLY public.hwsubmissiondevice
    ADD CONSTRAINT hwsubmissiondevice_submission_fkey FOREIGN KEY (submission) REFERENCES public.hwsubmission(id);


ALTER TABLE ONLY public.hwtestanswer
    ADD CONSTRAINT hwtestanswer__choice__test__fk FOREIGN KEY (test, choice) REFERENCES public.hwtestanswerchoice(test, id);


ALTER TABLE ONLY public.hwtestanswer
    ADD CONSTRAINT hwtestanswer_choice_fkey FOREIGN KEY (choice) REFERENCES public.hwtestanswerchoice(id);


ALTER TABLE ONLY public.hwtestanswer
    ADD CONSTRAINT hwtestanswer_language_fkey FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.hwtestanswer
    ADD CONSTRAINT hwtestanswer_submission_fkey FOREIGN KEY (submission) REFERENCES public.hwsubmission(id);


ALTER TABLE ONLY public.hwtestanswer
    ADD CONSTRAINT hwtestanswer_test_fkey FOREIGN KEY (test) REFERENCES public.hwtest(id);


ALTER TABLE ONLY public.hwtestanswerchoice
    ADD CONSTRAINT hwtestanswerchoice_test_fkey FOREIGN KEY (test) REFERENCES public.hwtest(id);


ALTER TABLE ONLY public.hwtestanswercount
    ADD CONSTRAINT hwtestanswercount_choice_fkey FOREIGN KEY (choice) REFERENCES public.hwtestanswerchoice(id);


ALTER TABLE ONLY public.hwtestanswercount
    ADD CONSTRAINT hwtestanswercount_distroarchseries_fkey FOREIGN KEY (distroarchseries) REFERENCES public.distroarchseries(id);


ALTER TABLE ONLY public.hwtestanswercount
    ADD CONSTRAINT hwtestanswercount_test_fkey FOREIGN KEY (test) REFERENCES public.hwtest(id);


ALTER TABLE ONLY public.hwtestanswercountdevice
    ADD CONSTRAINT hwtestanswercountdevice_answer_fkey FOREIGN KEY (answer) REFERENCES public.hwtestanswercount(id);


ALTER TABLE ONLY public.hwtestanswercountdevice
    ADD CONSTRAINT hwtestanswercountdevice_device_driver_fkey FOREIGN KEY (device_driver) REFERENCES public.hwdevicedriverlink(id);


ALTER TABLE ONLY public.hwtestanswerdevice
    ADD CONSTRAINT hwtestanswerdevice_answer_fkey FOREIGN KEY (answer) REFERENCES public.hwtestanswer(id);


ALTER TABLE ONLY public.hwtestanswerdevice
    ADD CONSTRAINT hwtestanswerdevice_device_driver_fkey FOREIGN KEY (device_driver) REFERENCES public.hwdevicedriverlink(id);


ALTER TABLE ONLY public.hwvendorid
    ADD CONSTRAINT hwvendorid_vendor_name_fkey FOREIGN KEY (vendor_name) REFERENCES public.hwvendorname(id);


ALTER TABLE ONLY public.ircid
    ADD CONSTRAINT ircid_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.jabberid
    ADD CONSTRAINT jabberid_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.packagingjob
    ADD CONSTRAINT job_fk FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_requester_fkey FOREIGN KEY (requester) REFERENCES public.person(id);


ALTER TABLE ONLY public.karma
    ADD CONSTRAINT karma_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.karma
    ADD CONSTRAINT karma_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.karma
    ADD CONSTRAINT karma_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.karma
    ADD CONSTRAINT karma_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.karmaaction
    ADD CONSTRAINT karmaaction_category_fk FOREIGN KEY (category) REFERENCES public.karmacategory(id);


ALTER TABLE ONLY public.karmacache
    ADD CONSTRAINT karmacache_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.karmacache
    ADD CONSTRAINT karmacache_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.karmacache
    ADD CONSTRAINT karmacache_project_fkey FOREIGN KEY (project) REFERENCES public.project(id);


ALTER TABLE ONLY public.karmacache
    ADD CONSTRAINT karmacache_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.karmatotalcache
    ADD CONSTRAINT karmatotalcache_person_fk FOREIGN KEY (person) REFERENCES public.person(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.languagepack
    ADD CONSTRAINT languagepack__file__fk FOREIGN KEY (file) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.languagepack
    ADD CONSTRAINT languagepack__updates__fk FOREIGN KEY (updates) REFERENCES public.languagepack(id);


ALTER TABLE ONLY public.languagepack
    ADD CONSTRAINT languagepackage__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT latestpersonsourcepackagereleasecache_publication_fkey FOREIGN KEY (publication) REFERENCES public.sourcepackagepublishinghistory(id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT latestpersonsourcepackagereleasecache_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT latestpersonsourcepackagereleasecache_sourcepackagerelease_fkey FOREIGN KEY (sourcepackagerelease) REFERENCES public.sourcepackagerelease(id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT latestpersonsourcepackagereleasecache_upload_archive_fkey FOREIGN KEY (upload_archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT latestpersonsourcepackagereleasecache_upload_distroseries_fkey FOREIGN KEY (upload_distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.libraryfilealias
    ADD CONSTRAINT libraryfilealias__content_fkey FOREIGN KEY (content) REFERENCES public.libraryfilecontent(id);


ALTER TABLE ONLY public.libraryfiledownloadcount
    ADD CONSTRAINT libraryfiledownloadcount__libraryfilealias__fk FOREIGN KEY (libraryfilealias) REFERENCES public.libraryfilealias(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.libraryfiledownloadcount
    ADD CONSTRAINT libraryfiledownloadcount_country_fkey FOREIGN KEY (country) REFERENCES public.country(id);


ALTER TABLE ONLY public.livefs
    ADD CONSTRAINT livefs_distro_series_fkey FOREIGN KEY (distro_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.livefs
    ADD CONSTRAINT livefs_owner_fkey FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.livefs
    ADD CONSTRAINT livefs_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_archive_fkey FOREIGN KEY (archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_build_farm_job_fkey FOREIGN KEY (build_farm_job) REFERENCES public.buildfarmjob(id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_builder_fkey FOREIGN KEY (builder) REFERENCES public.builder(id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_distro_arch_series_fkey FOREIGN KEY (distro_arch_series) REFERENCES public.distroarchseries(id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_livefs_fkey FOREIGN KEY (livefs) REFERENCES public.livefs(id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_log_fkey FOREIGN KEY (log) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_processor_fkey FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_requester_fkey FOREIGN KEY (requester) REFERENCES public.person(id);


ALTER TABLE ONLY public.livefsbuild
    ADD CONSTRAINT livefsbuild_upload_log_fkey FOREIGN KEY (upload_log) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.livefsfile
    ADD CONSTRAINT livefsfile_libraryfile_fkey FOREIGN KEY (libraryfile) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.livefsfile
    ADD CONSTRAINT livefsfile_livefsbuild_fkey FOREIGN KEY (livefsbuild) REFERENCES public.livefsbuild(id);


ALTER TABLE ONLY public.logintoken
    ADD CONSTRAINT logintoken_requester_fk FOREIGN KEY (requester) REFERENCES public.person(id);


ALTER TABLE ONLY public.mailinglist
    ADD CONSTRAINT mailinglist_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.mailinglist
    ADD CONSTRAINT mailinglist_reviewer_fkey FOREIGN KEY (reviewer) REFERENCES public.person(id);


ALTER TABLE ONLY public.mailinglist
    ADD CONSTRAINT mailinglist_team_fkey FOREIGN KEY (team) REFERENCES public.person(id);


ALTER TABLE ONLY public.mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription__email_address_fk FOREIGN KEY (email_address) REFERENCES public.emailaddress(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription_mailing_list_fkey FOREIGN KEY (mailing_list) REFERENCES public.mailinglist(id);


ALTER TABLE ONLY public.mailinglistsubscription
    ADD CONSTRAINT mailinglistsubscription_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.latestpersonsourcepackagereleasecache
    ADD CONSTRAINT maintainer_fkey FOREIGN KEY (maintainer) REFERENCES public.person(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_distribution_fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_parent_fk FOREIGN KEY (parent) REFERENCES public.message(id);


ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_raw_fk FOREIGN KEY (raw) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.messageapproval
    ADD CONSTRAINT messageapproval_disposed_by_fkey FOREIGN KEY (disposed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.messageapproval
    ADD CONSTRAINT messageapproval_mailing_list_fkey FOREIGN KEY (mailing_list) REFERENCES public.mailinglist(id);


ALTER TABLE ONLY public.messageapproval
    ADD CONSTRAINT messageapproval_message_fkey FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.messageapproval
    ADD CONSTRAINT messageapproval_posted_by_fkey FOREIGN KEY (posted_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.messageapproval
    ADD CONSTRAINT messageapproval_posted_message_fkey FOREIGN KEY (posted_message) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.messagechunk
    ADD CONSTRAINT messagechunk_blob_fk FOREIGN KEY (blob) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.messagechunk
    ADD CONSTRAINT messagechunk_message_fk FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone__distroseries__distribution__fk FOREIGN KEY (distroseries, distribution) REFERENCES public.distroseries(id, distribution);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_distribution_fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_product_fk FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_product_series_fk FOREIGN KEY (product, productseries) REFERENCES public.productseries(product, id);


ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_productseries_fk FOREIGN KEY (productseries) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.milestonetag
    ADD CONSTRAINT milestonetag_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.milestonetag
    ADD CONSTRAINT milestonetag_milestone_fkey FOREIGN KEY (milestone) REFERENCES public.milestone(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.mirrorcdimagedistroseries
    ADD CONSTRAINT mirrorcdimagedistroseries__distribution_mirror__fk FOREIGN KEY (distribution_mirror) REFERENCES public.distributionmirror(id);


ALTER TABLE ONLY public.mirrorcdimagedistroseries
    ADD CONSTRAINT mirrorcdimagedistroseries__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.mirrordistroarchseries
    ADD CONSTRAINT mirrordistroarchseries__component__fk FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.mirrordistroarchseries
    ADD CONSTRAINT mirrordistroarchseries__distribution_mirror__fk FOREIGN KEY (distribution_mirror) REFERENCES public.distributionmirror(id);


ALTER TABLE ONLY public.mirrordistroarchseries
    ADD CONSTRAINT mirrordistroarchseries__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES public.distroarchseries(id);


ALTER TABLE ONLY public.mirrordistroseriessource
    ADD CONSTRAINT mirrordistroseriessource__component__fk FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.mirrordistroseriessource
    ADD CONSTRAINT mirrordistroseriessource__distribution_mirror__fk FOREIGN KEY (distribution_mirror) REFERENCES public.distributionmirror(id);


ALTER TABLE ONLY public.mirrordistroseriessource
    ADD CONSTRAINT mirrordistroseriessource__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.mirrorproberecord
    ADD CONSTRAINT mirrorproberecord_distribution_mirror_fkey FOREIGN KEY (distribution_mirror) REFERENCES public.distributionmirror(id);


ALTER TABLE ONLY public.mirrorproberecord
    ADD CONSTRAINT mirrorproberecord_log_file_fkey FOREIGN KEY (log_file) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.nameblacklist
    ADD CONSTRAINT nameblacklist_admin_fk FOREIGN KEY (admin) REFERENCES public.person(id);


ALTER TABLE ONLY public.incrementaldiff
    ADD CONSTRAINT new_revision_fk FOREIGN KEY (new_revision) REFERENCES public.revision(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_consumer_fkey FOREIGN KEY (consumer) REFERENCES public.oauthconsumer(id);


ALTER TABLE ONLY public.oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_project_fkey FOREIGN KEY (project) REFERENCES public.project(id);


ALTER TABLE ONLY public.oauthaccesstoken
    ADD CONSTRAINT oauthaccesstoken_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_consumer_fkey FOREIGN KEY (consumer) REFERENCES public.oauthconsumer(id);


ALTER TABLE ONLY public.oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_project_fkey FOREIGN KEY (project) REFERENCES public.project(id);


ALTER TABLE ONLY public.oauthrequesttoken
    ADD CONSTRAINT oauthrequesttoken_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.officialbugtag
    ADD CONSTRAINT officialbugtag_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.officialbugtag
    ADD CONSTRAINT officialbugtag_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.officialbugtag
    ADD CONSTRAINT officialbugtag_project_fkey FOREIGN KEY (project) REFERENCES public.project(id);


ALTER TABLE ONLY public.incrementaldiff
    ADD CONSTRAINT old_revision_fk FOREIGN KEY (old_revision) REFERENCES public.revision(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.openididentifier
    ADD CONSTRAINT openididentifier_account_fkey FOREIGN KEY (account) REFERENCES public.account(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.packagecopyjob
    ADD CONSTRAINT packagecopyjob__job__fk FOREIGN KEY (job) REFERENCES public.job(id);


ALTER TABLE ONLY public.packagecopyjob
    ADD CONSTRAINT packagecopyjob_source_archive_fkey FOREIGN KEY (source_archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.packagecopyjob
    ADD CONSTRAINT packagecopyjob_target_archive_fkey FOREIGN KEY (target_archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.packagecopyjob
    ADD CONSTRAINT packagecopyjob_target_distroseries_fkey FOREIGN KEY (target_distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.packagecopyrequest
    ADD CONSTRAINT packagecopyrequest__sourcearchive__fk FOREIGN KEY (source_archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.packagecopyrequest
    ADD CONSTRAINT packagecopyrequest__targetarchive__fk FOREIGN KEY (target_archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_requester_fk FOREIGN KEY (requester) REFERENCES public.person(id);


ALTER TABLE ONLY public.packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_sourcecomponent_fk FOREIGN KEY (source_component) REFERENCES public.component(id);


ALTER TABLE ONLY public.packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_sourcedistroseries_fk FOREIGN KEY (source_distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_targetcomponent_fk FOREIGN KEY (target_component) REFERENCES public.component(id);


ALTER TABLE ONLY public.packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_targetdistroseries_fk FOREIGN KEY (target_distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.packagediff
    ADD CONSTRAINT packagediff_diff_content_fkey FOREIGN KEY (diff_content) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.packagediff
    ADD CONSTRAINT packagediff_from_source_fkey FOREIGN KEY (from_source) REFERENCES public.sourcepackagerelease(id);


ALTER TABLE ONLY public.packagediff
    ADD CONSTRAINT packagediff_requester_fkey FOREIGN KEY (requester) REFERENCES public.person(id);


ALTER TABLE ONLY public.packagediff
    ADD CONSTRAINT packagediff_to_source_fkey FOREIGN KEY (to_source) REFERENCES public.sourcepackagerelease(id);


ALTER TABLE ONLY public.packageset
    ADD CONSTRAINT packageset__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.packageset
    ADD CONSTRAINT packageset__owner__fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.packageset
    ADD CONSTRAINT packageset__packagesetgroup__fk FOREIGN KEY (packagesetgroup) REFERENCES public.packagesetgroup(id);


ALTER TABLE ONLY public.packagesetgroup
    ADD CONSTRAINT packagesetgroup__owner__fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.packagesetinclusion
    ADD CONSTRAINT packagesetinclusion__child__fk FOREIGN KEY (child) REFERENCES public.packageset(id);


ALTER TABLE ONLY public.packagesetinclusion
    ADD CONSTRAINT packagesetinclusion__parent__fk FOREIGN KEY (parent) REFERENCES public.packageset(id);


ALTER TABLE ONLY public.packagesetsources
    ADD CONSTRAINT packagesetsources__packageset__fk FOREIGN KEY (packageset) REFERENCES public.packageset(id);


ALTER TABLE ONLY public.packageupload
    ADD CONSTRAINT packageupload__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.packageupload
    ADD CONSTRAINT packageupload__changesfile__fk FOREIGN KEY (changesfile) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.packageupload
    ADD CONSTRAINT packageupload__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.packageupload
    ADD CONSTRAINT packageupload__package_copy_job__fk FOREIGN KEY (package_copy_job) REFERENCES public.packagecopyjob(id);


ALTER TABLE ONLY public.packageupload
    ADD CONSTRAINT packageupload__signing_key__fk FOREIGN KEY (signing_key) REFERENCES public.gpgkey(id);


ALTER TABLE ONLY public.packageupload
    ADD CONSTRAINT packageupload_signing_key_owner_fkey FOREIGN KEY (signing_key_owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.packageuploadbuild
    ADD CONSTRAINT packageuploadbuild__packageupload__fk FOREIGN KEY (packageupload) REFERENCES public.packageupload(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.packageuploadbuild
    ADD CONSTRAINT packageuploadbuild_build_fk FOREIGN KEY (build) REFERENCES public.binarypackagebuild(id);


ALTER TABLE ONLY public.packageuploadcustom
    ADD CONSTRAINT packageuploadcustom_libraryfilealias_fk FOREIGN KEY (libraryfilealias) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.packageuploadcustom
    ADD CONSTRAINT packageuploadcustom_packageupload_fk FOREIGN KEY (packageupload) REFERENCES public.packageupload(id);


ALTER TABLE ONLY public.packageuploadsource
    ADD CONSTRAINT packageuploadsource__packageupload__fk FOREIGN KEY (packageupload) REFERENCES public.packageupload(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.packageuploadsource
    ADD CONSTRAINT packageuploadsource__sourcepackagerelease__fk FOREIGN KEY (sourcepackagerelease) REFERENCES public.sourcepackagerelease(id);


ALTER TABLE ONLY public.packaging
    ADD CONSTRAINT packaging__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.packaging
    ADD CONSTRAINT packaging_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.packaging
    ADD CONSTRAINT packaging_productseries_fk FOREIGN KEY (productseries) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.packaging
    ADD CONSTRAINT packaging_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person__account__fk FOREIGN KEY (account) REFERENCES public.account(id);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person__icon__fk FOREIGN KEY (icon) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person__logo__fk FOREIGN KEY (logo) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person__mugshot__fk FOREIGN KEY (mugshot) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.karmacache
    ADD CONSTRAINT person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person_language_fk FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person_merged_fk FOREIGN KEY (merged) REFERENCES public.person(id);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person_registrant_fk FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.person
    ADD CONSTRAINT person_teamowner_fk FOREIGN KEY (teamowner) REFERENCES public.person(id);


ALTER TABLE ONLY public.personlanguage
    ADD CONSTRAINT personlanguage_language_fk FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.personlanguage
    ADD CONSTRAINT personlanguage_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.personlocation
    ADD CONSTRAINT personlocation_last_modified_by_fkey FOREIGN KEY (last_modified_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.personlocation
    ADD CONSTRAINT personlocation_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.personnotification
    ADD CONSTRAINT personnotification_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.personsettings
    ADD CONSTRAINT personsettings_person_fkey FOREIGN KEY (person) REFERENCES public.person(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.persontransferjob
    ADD CONSTRAINT persontransferjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id);


ALTER TABLE ONLY public.persontransferjob
    ADD CONSTRAINT persontransferjob_major_person_fkey FOREIGN KEY (major_person) REFERENCES public.person(id);


ALTER TABLE ONLY public.persontransferjob
    ADD CONSTRAINT persontransferjob_minor_person_fkey FOREIGN KEY (minor_person) REFERENCES public.person(id);


ALTER TABLE ONLY public.pillarname
    ADD CONSTRAINT pillarname__alias_for__fk FOREIGN KEY (alias_for) REFERENCES public.pillarname(id);


ALTER TABLE ONLY public.pillarname
    ADD CONSTRAINT pillarname_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.pillarname
    ADD CONSTRAINT pillarname_product_fkey FOREIGN KEY (product) REFERENCES public.product(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.pillarname
    ADD CONSTRAINT pillarname_project_fkey FOREIGN KEY (project) REFERENCES public.project(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.pocketchroot
    ADD CONSTRAINT pocketchroot__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES public.distroarchseries(id);


ALTER TABLE ONLY public.pocketchroot
    ADD CONSTRAINT pocketchroot__libraryfilealias__fk FOREIGN KEY (chroot) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.poexportrequest
    ADD CONSTRAINT poeportrequest_potemplate_fk FOREIGN KEY (potemplate) REFERENCES public.potemplate(id);


ALTER TABLE ONLY public.poexportrequest
    ADD CONSTRAINT poexportrequest_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.poexportrequest
    ADD CONSTRAINT poexportrequest_pofile_fk FOREIGN KEY (pofile) REFERENCES public.pofile(id);


ALTER TABLE ONLY public.pofile
    ADD CONSTRAINT pofile_language_fk FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.pofile
    ADD CONSTRAINT pofile_lasttranslator_fk FOREIGN KEY (lasttranslator) REFERENCES public.person(id);


ALTER TABLE ONLY public.pofile
    ADD CONSTRAINT pofile_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.pofile
    ADD CONSTRAINT pofile_potemplate_fk FOREIGN KEY (potemplate) REFERENCES public.potemplate(id);


ALTER TABLE ONLY public.pofilestatsjob
    ADD CONSTRAINT pofilestatsjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id);


ALTER TABLE ONLY public.pofilestatsjob
    ADD CONSTRAINT pofilestatsjob_pofile_fkey FOREIGN KEY (pofile) REFERENCES public.pofile(id);


ALTER TABLE ONLY public.pofiletranslator
    ADD CONSTRAINT pofiletranslator__person__fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.pofiletranslator
    ADD CONSTRAINT pofiletranslator__pofile__fk FOREIGN KEY (pofile) REFERENCES public.pofile(id);


ALTER TABLE ONLY public.poll
    ADD CONSTRAINT poll_team_fk FOREIGN KEY (team) REFERENCES public.person(id);


ALTER TABLE ONLY public.potemplate
    ADD CONSTRAINT potemplate__distrorelease__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.potemplate
    ADD CONSTRAINT potemplate__from_sourcepackagename__fk FOREIGN KEY (from_sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.potemplate
    ADD CONSTRAINT potemplate__source_file__fk FOREIGN KEY (source_file) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.potemplate
    ADD CONSTRAINT potemplate_binarypackagename_fk FOREIGN KEY (binarypackagename) REFERENCES public.binarypackagename(id);


ALTER TABLE ONLY public.packagingjob
    ADD CONSTRAINT potemplate_fk FOREIGN KEY (potemplate) REFERENCES public.potemplate(id);


ALTER TABLE ONLY public.potemplate
    ADD CONSTRAINT potemplate_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.potemplate
    ADD CONSTRAINT potemplate_productseries_fk FOREIGN KEY (productseries) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.potemplate
    ADD CONSTRAINT potemplate_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.potmsgset
    ADD CONSTRAINT potmsgset__msgid_plural__fk FOREIGN KEY (msgid_plural) REFERENCES public.pomsgid(id);


ALTER TABLE ONLY public.potmsgset
    ADD CONSTRAINT potmsgset_primemsgid_fk FOREIGN KEY (msgid_singular) REFERENCES public.pomsgid(id);


ALTER TABLE ONLY public.previewdiff
    ADD CONSTRAINT previewdiff_branch_merge_proposal_fkey FOREIGN KEY (branch_merge_proposal) REFERENCES public.branchmergeproposal(id);


ALTER TABLE ONLY public.previewdiff
    ADD CONSTRAINT previewdiff_diff_fkey FOREIGN KEY (diff) REFERENCES public.diff(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.processacceptedbugsjob
    ADD CONSTRAINT processacceptedbugsjob_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.processacceptedbugsjob
    ADD CONSTRAINT processacceptedbugsjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.processacceptedbugsjob
    ADD CONSTRAINT processacceptedbugsjob_sourcepackagerelease_fkey FOREIGN KEY (sourcepackagerelease) REFERENCES public.sourcepackagerelease(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product__development_focus__fk FOREIGN KEY (development_focus) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product__icon__fk FOREIGN KEY (icon) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product__logo__fk FOREIGN KEY (logo) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product__mugshot__fk FOREIGN KEY (mugshot) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product__translation_focus__fk FOREIGN KEY (translation_focus) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_bugtracker_fkey FOREIGN KEY (bugtracker) REFERENCES public.bugtracker(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_driver_fk FOREIGN KEY (driver) REFERENCES public.person(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_project_fk FOREIGN KEY (project) REFERENCES public.project(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES public.translationgroup(id);


ALTER TABLE ONLY public.productjob
    ADD CONSTRAINT productjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.productjob
    ADD CONSTRAINT productjob_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.productlicense
    ADD CONSTRAINT productlicense_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.productrelease
    ADD CONSTRAINT productrelease_milestone_fkey FOREIGN KEY (milestone) REFERENCES public.milestone(id);


ALTER TABLE ONLY public.productrelease
    ADD CONSTRAINT productrelease_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.productreleasefile
    ADD CONSTRAINT productreleasefile__signature__fk FOREIGN KEY (signature) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.productreleasefile
    ADD CONSTRAINT productreleasefile__uploader__fk FOREIGN KEY (uploader) REFERENCES public.person(id);


ALTER TABLE ONLY public.productseries
    ADD CONSTRAINT productseries_branch_fkey FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.productseries
    ADD CONSTRAINT productseries_driver_fk FOREIGN KEY (driver) REFERENCES public.person(id);


ALTER TABLE ONLY public.packagingjob
    ADD CONSTRAINT productseries_fk FOREIGN KEY (productseries) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.productseries
    ADD CONSTRAINT productseries_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.productseries
    ADD CONSTRAINT productseries_product_fk FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.productseries
    ADD CONSTRAINT productseries_translations_branch_fkey FOREIGN KEY (translations_branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project__icon__fk FOREIGN KEY (icon) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project__logo__fk FOREIGN KEY (logo) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project__mugshot__fk FOREIGN KEY (mugshot) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_bugtracker_fkey FOREIGN KEY (bugtracker) REFERENCES public.bugtracker(id);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_driver_fk FOREIGN KEY (driver) REFERENCES public.person(id);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES public.translationgroup(id);


ALTER TABLE ONLY public.publisherconfig
    ADD CONSTRAINT publisherconfig__distribution__fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT question__answer__fk FOREIGN KEY (answer) REFERENCES public.questionmessage(id);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT question__answerer__fk FOREIGN KEY (answerer) REFERENCES public.person(id);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT question__assignee__fk FOREIGN KEY (assignee) REFERENCES public.person(id);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT question__distribution__fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT question__faq__fk FOREIGN KEY (faq) REFERENCES public.faq(id);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT question__language__fkey FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT question__owner__fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT question__product__fk FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.question
    ADD CONSTRAINT question__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.questionjob
    ADD CONSTRAINT questionjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id);


ALTER TABLE ONLY public.questionjob
    ADD CONSTRAINT questionjob_question_fkey FOREIGN KEY (question) REFERENCES public.question(id);


ALTER TABLE ONLY public.questionmessage
    ADD CONSTRAINT questionmessage__message__fk FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.questionmessage
    ADD CONSTRAINT questionmessage__question__fk FOREIGN KEY (question) REFERENCES public.question(id);


ALTER TABLE ONLY public.questionreopening
    ADD CONSTRAINT questionreopening__answerer__fk FOREIGN KEY (answerer) REFERENCES public.person(id);


ALTER TABLE ONLY public.questionreopening
    ADD CONSTRAINT questionreopening__question__fk FOREIGN KEY (question) REFERENCES public.question(id);


ALTER TABLE ONLY public.questionreopening
    ADD CONSTRAINT questionreopening__reopener__fk FOREIGN KEY (reopener) REFERENCES public.person(id);


ALTER TABLE ONLY public.questionsubscription
    ADD CONSTRAINT questionsubscription__person__fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.questionsubscription
    ADD CONSTRAINT questionsubscription__question__fk FOREIGN KEY (question) REFERENCES public.question(id);


ALTER TABLE ONLY public.gitrulegrant
    ADD CONSTRAINT repository_matches_rule FOREIGN KEY (repository, rule) REFERENCES public.gitrule(repository, id);


ALTER TABLE ONLY public.teammembership
    ADD CONSTRAINT reviewer_fk FOREIGN KEY (last_changed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.revision
    ADD CONSTRAINT revision_gpgkey_fk FOREIGN KEY (gpgkey) REFERENCES public.gpgkey(id);


ALTER TABLE ONLY public.revision
    ADD CONSTRAINT revision_revision_author_fk FOREIGN KEY (revision_author) REFERENCES public.revisionauthor(id);


ALTER TABLE ONLY public.revision
    ADD CONSTRAINT revision_signing_key_owner_fkey FOREIGN KEY (signing_key_owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.revisionauthor
    ADD CONSTRAINT revisionauthor_person_fkey FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.revisioncache
    ADD CONSTRAINT revisioncache__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.revisioncache
    ADD CONSTRAINT revisioncache__product__fk FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.revisioncache
    ADD CONSTRAINT revisioncache__revision__fk FOREIGN KEY (revision) REFERENCES public.revision(id);


ALTER TABLE ONLY public.revisioncache
    ADD CONSTRAINT revisioncache__revision_author__fk FOREIGN KEY (revision_author) REFERENCES public.revisionauthor(id);


ALTER TABLE ONLY public.revisioncache
    ADD CONSTRAINT revisioncache__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.revisionparent
    ADD CONSTRAINT revisionparent_revision_fk FOREIGN KEY (revision) REFERENCES public.revision(id);


ALTER TABLE ONLY public.revisionproperty
    ADD CONSTRAINT revisionproperty__revision__fk FOREIGN KEY (revision) REFERENCES public.revision(id);


ALTER TABLE ONLY public.sectionselection
    ADD CONSTRAINT sectionselection__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.sectionselection
    ADD CONSTRAINT sectionselection__section__fk FOREIGN KEY (section) REFERENCES public.section(id);


ALTER TABLE ONLY public.binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory__distroarchseries__fk FOREIGN KEY (distroarchseries) REFERENCES public.distroarchseries(id);


ALTER TABLE ONLY public.binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_binarypackagerelease_fk FOREIGN KEY (binarypackagerelease) REFERENCES public.binarypackagerelease(id);


ALTER TABLE ONLY public.binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_component_fk FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_removedby_fk FOREIGN KEY (removed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.binarypackagepublishinghistory
    ADD CONSTRAINT securebinarypackagepublishinghistory_section_fk FOREIGN KEY (section) REFERENCES public.section(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_component_fk FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_removedby_fk FOREIGN KEY (removed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_section_fk FOREIGN KEY (section) REFERENCES public.section(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_sourcepackagerelease_fk FOREIGN KEY (sourcepackagerelease) REFERENCES public.sourcepackagerelease(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT securesourcepackagepublishinghistory_supersededby_fk FOREIGN KEY (supersededby) REFERENCES public.sourcepackagerelease(id);


ALTER TABLE ONLY public.seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_branch_fkey FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.seriessourcepackagebranch
    ADD CONSTRAINT seriessourcepackagebranch_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.sharingjob
    ADD CONSTRAINT sharingjob_distro_fkey FOREIGN KEY (distro) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.sharingjob
    ADD CONSTRAINT sharingjob_grantee_fkey FOREIGN KEY (grantee) REFERENCES public.person(id);


ALTER TABLE ONLY public.sharingjob
    ADD CONSTRAINT sharingjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.sharingjob
    ADD CONSTRAINT sharingjob_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.signedcodeofconduct
    ADD CONSTRAINT signedcodeofconduct_signingkey_fk FOREIGN KEY (owner, signingkey) REFERENCES public.gpgkey(owner, id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.snap
    ADD CONSTRAINT snap_auto_build_archive_fkey FOREIGN KEY (auto_build_archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.snap
    ADD CONSTRAINT snap_branch_fkey FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.snap
    ADD CONSTRAINT snap_distro_series_fkey FOREIGN KEY (distro_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.snap
    ADD CONSTRAINT snap_git_repository_fkey FOREIGN KEY (git_repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.snap
    ADD CONSTRAINT snap_owner_fkey FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.snap
    ADD CONSTRAINT snap_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.snap
    ADD CONSTRAINT snap_store_series_fkey FOREIGN KEY (store_series) REFERENCES public.snappyseries(id);


ALTER TABLE ONLY public.snaparch
    ADD CONSTRAINT snaparch_processor_fkey FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.snaparch
    ADD CONSTRAINT snaparch_snap_fkey FOREIGN KEY (snap) REFERENCES public.snap(id);


ALTER TABLE ONLY public.snapbase
    ADD CONSTRAINT snapbase_distro_series_fkey FOREIGN KEY (distro_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.snapbase
    ADD CONSTRAINT snapbase_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_archive_fkey FOREIGN KEY (archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_build_farm_job_fkey FOREIGN KEY (build_farm_job) REFERENCES public.buildfarmjob(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_build_request_fkey FOREIGN KEY (build_request) REFERENCES public.job(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_builder_fkey FOREIGN KEY (builder) REFERENCES public.builder(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_distro_arch_series_fkey FOREIGN KEY (distro_arch_series) REFERENCES public.distroarchseries(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_log_fkey FOREIGN KEY (log) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_processor_fkey FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_requester_fkey FOREIGN KEY (requester) REFERENCES public.person(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_snap_fkey FOREIGN KEY (snap) REFERENCES public.snap(id);


ALTER TABLE ONLY public.snapbuild
    ADD CONSTRAINT snapbuild_upload_log_fkey FOREIGN KEY (upload_log) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.snapbuildjob
    ADD CONSTRAINT snapbuildjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.snapbuildjob
    ADD CONSTRAINT snapbuildjob_snapbuild_fkey FOREIGN KEY (snapbuild) REFERENCES public.snapbuild(id);


ALTER TABLE ONLY public.snapfile
    ADD CONSTRAINT snapfile_libraryfile_fkey FOREIGN KEY (libraryfile) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.snapfile
    ADD CONSTRAINT snapfile_snapbuild_fkey FOREIGN KEY (snapbuild) REFERENCES public.snapbuild(id);


ALTER TABLE ONLY public.snapjob
    ADD CONSTRAINT snapjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.snapjob
    ADD CONSTRAINT snapjob_snap_fkey FOREIGN KEY (snap) REFERENCES public.snap(id);


ALTER TABLE ONLY public.snappydistroseries
    ADD CONSTRAINT snappydistroseries_distro_series_fkey FOREIGN KEY (distro_series) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.snappydistroseries
    ADD CONSTRAINT snappydistroseries_snappy_series_fkey FOREIGN KEY (snappy_series) REFERENCES public.snappyseries(id);


ALTER TABLE ONLY public.snappyseries
    ADD CONSTRAINT snappyseries_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackageformatselection
    ADD CONSTRAINT sourceformatselection__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.packagingjob
    ADD CONSTRAINT sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.packagesetsources
    ADD CONSTRAINT sourcepackagenamesources__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory__archive__fk FOREIGN KEY (archive) REFERENCES public.archive(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory__creator__fk FOREIGN KEY (creator) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory__sponsor__fk FOREIGN KEY (sponsor) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_ancestor_fkey FOREIGN KEY (ancestor) REFERENCES public.sourcepackagepublishinghistory(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_packageupload_fkey FOREIGN KEY (packageupload) REFERENCES public.packageupload(id);


ALTER TABLE ONLY public.sourcepackagepublishinghistory
    ADD CONSTRAINT sourcepackagepublishinghistory_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe_daily_build_archive_fkey FOREIGN KEY (daily_build_archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe_owner_fkey FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackagerecipe
    ADD CONSTRAINT sourcepackagerecipe_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_archive_fkey FOREIGN KEY (archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_build_farm_job_fkey FOREIGN KEY (build_farm_job) REFERENCES public.buildfarmjob(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_builder_fkey FOREIGN KEY (builder) REFERENCES public.builder(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_log_fkey FOREIGN KEY (log) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_manifest_fkey FOREIGN KEY (manifest) REFERENCES public.sourcepackagerecipedata(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_processor_fkey FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_recipe_fkey FOREIGN KEY (recipe) REFERENCES public.sourcepackagerecipe(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_requester_fkey FOREIGN KEY (requester) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackagerecipebuild
    ADD CONSTRAINT sourcepackagerecipebuild_upload_log_fkey FOREIGN KEY (upload_log) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.sourcepackagerecipedata
    ADD CONSTRAINT sourcepackagerecipedata_base_branch_fkey FOREIGN KEY (base_branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.sourcepackagerecipedata
    ADD CONSTRAINT sourcepackagerecipedata_base_git_repository_fkey FOREIGN KEY (base_git_repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.sourcepackagerecipedata
    ADD CONSTRAINT sourcepackagerecipedata_sourcepackage_recipe_build_fkey FOREIGN KEY (sourcepackage_recipe_build) REFERENCES public.sourcepackagerecipebuild(id);


ALTER TABLE ONLY public.sourcepackagerecipedata
    ADD CONSTRAINT sourcepackagerecipedata_sourcepackage_recipe_fkey FOREIGN KEY (sourcepackage_recipe) REFERENCES public.sourcepackagerecipe(id);


ALTER TABLE ONLY public.sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction_branch_fkey FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction_git_repository_fkey FOREIGN KEY (git_repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction_parent_instruction_fkey FOREIGN KEY (parent_instruction) REFERENCES public.sourcepackagerecipedatainstruction(id);


ALTER TABLE ONLY public.sourcepackagerecipedatainstruction
    ADD CONSTRAINT sourcepackagerecipedatainstruction_recipe_data_fkey FOREIGN KEY (recipe_data) REFERENCES public.sourcepackagerecipedata(id);


ALTER TABLE ONLY public.sourcepackagerecipedistroseries
    ADD CONSTRAINT sourcepackagerecipedistroseries_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.sourcepackagerecipedistroseries
    ADD CONSTRAINT sourcepackagerecipedistroseries_sourcepackagerecipe_fkey FOREIGN KEY (sourcepackagerecipe) REFERENCES public.sourcepackagerecipe(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__creator__fk FOREIGN KEY (creator) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__dscsigningkey FOREIGN KEY (dscsigningkey) REFERENCES public.gpgkey(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__upload_archive__fk FOREIGN KEY (upload_archive) REFERENCES public.archive(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease__upload_distroseries__fk FOREIGN KEY (upload_distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_buildinfo_fkey FOREIGN KEY (buildinfo) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_changelog_fkey FOREIGN KEY (changelog) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_component_fk FOREIGN KEY (component) REFERENCES public.component(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_maintainer_fk FOREIGN KEY (maintainer) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_section FOREIGN KEY (section) REFERENCES public.section(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_signing_key_owner_fkey FOREIGN KEY (signing_key_owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_sourcepackage_recipe_build_fkey FOREIGN KEY (sourcepackage_recipe_build) REFERENCES public.sourcepackagerecipebuild(id);


ALTER TABLE ONLY public.sourcepackagerelease
    ADD CONSTRAINT sourcepackagerelease_sourcepackagename_fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification__distroseries__distribution__fk FOREIGN KEY (distroseries, distribution) REFERENCES public.distroseries(id, distribution);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_approver_fk FOREIGN KEY (approver) REFERENCES public.person(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_assignee_fk FOREIGN KEY (assignee) REFERENCES public.person(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_completer_fkey FOREIGN KEY (completer) REFERENCES public.person(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_distribution_fk FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_distribution_milestone_fk FOREIGN KEY (distribution, milestone) REFERENCES public.milestone(distribution, id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_drafter_fk FOREIGN KEY (drafter) REFERENCES public.person(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_goal_decider_fkey FOREIGN KEY (goal_decider) REFERENCES public.person(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_goal_proposer_fkey FOREIGN KEY (goal_proposer) REFERENCES public.person(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_last_changed_by_fkey FOREIGN KEY (last_changed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_product_fk FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_product_milestone_fk FOREIGN KEY (product, milestone) REFERENCES public.milestone(product, id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_productseries_valid FOREIGN KEY (product, productseries) REFERENCES public.productseries(product, id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_starter_fkey FOREIGN KEY (starter) REFERENCES public.person(id);


ALTER TABLE ONLY public.specification
    ADD CONSTRAINT specification_superseded_by_fk FOREIGN KEY (superseded_by) REFERENCES public.specification(id);


ALTER TABLE ONLY public.specificationbranch
    ADD CONSTRAINT specificationbranch__branch__fk FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.specificationbranch
    ADD CONSTRAINT specificationbranch__specification__fk FOREIGN KEY (specification) REFERENCES public.specification(id);


ALTER TABLE ONLY public.specificationbranch
    ADD CONSTRAINT specificationbranch_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.specificationdependency
    ADD CONSTRAINT specificationdependency_dependency_fk FOREIGN KEY (dependency) REFERENCES public.specification(id);


ALTER TABLE ONLY public.specificationdependency
    ADD CONSTRAINT specificationdependency_specification_fk FOREIGN KEY (specification) REFERENCES public.specification(id);


ALTER TABLE ONLY public.specificationmessage
    ADD CONSTRAINT specificationmessage__message__fk FOREIGN KEY (message) REFERENCES public.message(id);


ALTER TABLE ONLY public.specificationmessage
    ADD CONSTRAINT specificationmessage__specification__fk FOREIGN KEY (specification) REFERENCES public.specification(id);


ALTER TABLE ONLY public.specificationsubscription
    ADD CONSTRAINT specificationsubscription_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.specificationsubscription
    ADD CONSTRAINT specificationsubscription_specification_fk FOREIGN KEY (specification) REFERENCES public.specification(id);


ALTER TABLE ONLY public.specificationworkitem
    ADD CONSTRAINT specificationworkitem_assignee_fkey FOREIGN KEY (assignee) REFERENCES public.person(id);


ALTER TABLE ONLY public.specificationworkitem
    ADD CONSTRAINT specificationworkitem_milestone_fkey FOREIGN KEY (milestone) REFERENCES public.milestone(id);


ALTER TABLE ONLY public.specificationworkitem
    ADD CONSTRAINT specificationworkitem_specification_fkey FOREIGN KEY (specification) REFERENCES public.specification(id);


ALTER TABLE ONLY public.sprint
    ADD CONSTRAINT sprint__icon__fk FOREIGN KEY (icon) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.sprint
    ADD CONSTRAINT sprint__logo__fk FOREIGN KEY (logo) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.sprint
    ADD CONSTRAINT sprint__mugshot__fk FOREIGN KEY (mugshot) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.sprint
    ADD CONSTRAINT sprint_driver_fkey FOREIGN KEY (driver) REFERENCES public.person(id);


ALTER TABLE ONLY public.sprint
    ADD CONSTRAINT sprint_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.sprintattendance
    ADD CONSTRAINT sprintattendance_attendee_fk FOREIGN KEY (attendee) REFERENCES public.person(id);


ALTER TABLE ONLY public.sprintattendance
    ADD CONSTRAINT sprintattendance_sprint_fk FOREIGN KEY (sprint) REFERENCES public.sprint(id);


ALTER TABLE ONLY public.sprintspecification
    ADD CONSTRAINT sprintspec_spec_fk FOREIGN KEY (specification) REFERENCES public.specification(id);


ALTER TABLE ONLY public.sprintspecification
    ADD CONSTRAINT sprintspec_sprint_fk FOREIGN KEY (sprint) REFERENCES public.sprint(id);


ALTER TABLE ONLY public.sprintspecification
    ADD CONSTRAINT sprintspecification__nominator__fk FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.sprintspecification
    ADD CONSTRAINT sprintspecification_decider_fkey FOREIGN KEY (decider) REFERENCES public.person(id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_distribution_fkey FOREIGN KEY (distribution) REFERENCES public.distribution(id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_distroseries_fkey FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_milestone_fkey FOREIGN KEY (milestone) REFERENCES public.milestone(id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_product_fkey FOREIGN KEY (product) REFERENCES public.product(id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_productseries_fkey FOREIGN KEY (productseries) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_project_fkey FOREIGN KEY (project) REFERENCES public.project(id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_sourcepackagename_fkey FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_subscribed_by_fkey FOREIGN KEY (subscribed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.structuralsubscription
    ADD CONSTRAINT structuralsubscription_subscriber_fkey FOREIGN KEY (subscriber) REFERENCES public.person(id);


ALTER TABLE ONLY public.suggestivepotemplate
    ADD CONSTRAINT suggestivepotemplate__potemplate__fk FOREIGN KEY (potemplate) REFERENCES public.potemplate(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.teammembership
    ADD CONSTRAINT teammembership_acknowledged_by_fkey FOREIGN KEY (acknowledged_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.teammembership
    ADD CONSTRAINT teammembership_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.teammembership
    ADD CONSTRAINT teammembership_proposed_by_fkey FOREIGN KEY (proposed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.teammembership
    ADD CONSTRAINT teammembership_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.person(id);


ALTER TABLE ONLY public.teammembership
    ADD CONSTRAINT teammembership_team_fk FOREIGN KEY (team) REFERENCES public.person(id);


ALTER TABLE ONLY public.teamparticipation
    ADD CONSTRAINT teamparticipation_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.teamparticipation
    ADD CONSTRAINT teamparticipation_team_fk FOREIGN KEY (team) REFERENCES public.person(id);


ALTER TABLE ONLY public.temporaryblobstorage
    ADD CONSTRAINT temporaryblobstorage_file_alias_fkey FOREIGN KEY (file_alias) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.translationgroup
    ADD CONSTRAINT translationgroup_owner_fk FOREIGN KEY (owner) REFERENCES public.person(id);


ALTER TABLE ONLY public.translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__content__fk FOREIGN KEY (content) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__distroseries__fk FOREIGN KEY (distroseries) REFERENCES public.distroseries(id);


ALTER TABLE ONLY public.translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__importer__fk FOREIGN KEY (importer) REFERENCES public.person(id);


ALTER TABLE ONLY public.translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__pofile__fk FOREIGN KEY (pofile) REFERENCES public.pofile(id);


ALTER TABLE ONLY public.translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__potemplate__fk FOREIGN KEY (potemplate) REFERENCES public.potemplate(id);


ALTER TABLE ONLY public.translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__productseries__fk FOREIGN KEY (productseries) REFERENCES public.productseries(id);


ALTER TABLE ONLY public.translationimportqueueentry
    ADD CONSTRAINT translationimportqueueentry__sourcepackagename__fk FOREIGN KEY (sourcepackagename) REFERENCES public.sourcepackagename(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage__msgstr0__fk FOREIGN KEY (msgstr0) REFERENCES public.potranslation(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage__msgstr1__fk FOREIGN KEY (msgstr1) REFERENCES public.potranslation(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage__msgstr2__fk FOREIGN KEY (msgstr2) REFERENCES public.potranslation(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage__msgstr3__fk FOREIGN KEY (msgstr3) REFERENCES public.potranslation(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage__msgstr4__fk FOREIGN KEY (msgstr4) REFERENCES public.potranslation(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage__msgstr5__fk FOREIGN KEY (msgstr5) REFERENCES public.potranslation(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage__potmsgset__fk FOREIGN KEY (potmsgset) REFERENCES public.potmsgset(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage__reviewer__fk FOREIGN KEY (reviewer) REFERENCES public.person(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage__submitter__fk FOREIGN KEY (submitter) REFERENCES public.person(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage_language_fkey FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage_msgid_plural_fkey FOREIGN KEY (msgid_plural) REFERENCES public.pomsgid(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage_msgid_singular_fkey FOREIGN KEY (msgid_singular) REFERENCES public.pomsgid(id);


ALTER TABLE ONLY public.translationmessage
    ADD CONSTRAINT translationmessage_potemplate_fkey FOREIGN KEY (potemplate) REFERENCES public.potemplate(id);


ALTER TABLE ONLY public.translationrelicensingagreement
    ADD CONSTRAINT translationrelicensingagreement__person__fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.translationtemplateitem
    ADD CONSTRAINT translationtemplateitem_msgid_plural_fkey FOREIGN KEY (msgid_plural) REFERENCES public.pomsgid(id);


ALTER TABLE ONLY public.translationtemplateitem
    ADD CONSTRAINT translationtemplateitem_msgid_singular_fkey FOREIGN KEY (msgid_singular) REFERENCES public.pomsgid(id);


ALTER TABLE ONLY public.translationtemplateitem
    ADD CONSTRAINT translationtemplateitem_potemplate_fkey FOREIGN KEY (potemplate) REFERENCES public.potemplate(id);


ALTER TABLE ONLY public.translationtemplateitem
    ADD CONSTRAINT translationtemplateitem_potmsgset_fkey FOREIGN KEY (potmsgset) REFERENCES public.potmsgset(id);


ALTER TABLE ONLY public.translationtemplatesbuild
    ADD CONSTRAINT translationtemplatesbuild_branch_fkey FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.translationtemplatesbuild
    ADD CONSTRAINT translationtemplatesbuild_build_farm_job_fkey FOREIGN KEY (build_farm_job) REFERENCES public.buildfarmjob(id);


ALTER TABLE ONLY public.translationtemplatesbuild
    ADD CONSTRAINT translationtemplatesbuild_builder_fkey FOREIGN KEY (builder) REFERENCES public.builder(id);


ALTER TABLE ONLY public.translationtemplatesbuild
    ADD CONSTRAINT translationtemplatesbuild_log_fkey FOREIGN KEY (log) REFERENCES public.libraryfilealias(id);


ALTER TABLE ONLY public.translationtemplatesbuild
    ADD CONSTRAINT translationtemplatesbuild_processor_fkey FOREIGN KEY (processor) REFERENCES public.processor(id);


ALTER TABLE ONLY public.translator
    ADD CONSTRAINT translator_language_fk FOREIGN KEY (language) REFERENCES public.language(id);


ALTER TABLE ONLY public.translator
    ADD CONSTRAINT translator_person_fk FOREIGN KEY (translator) REFERENCES public.person(id);


ALTER TABLE ONLY public.translator
    ADD CONSTRAINT translator_translationgroup_fk FOREIGN KEY (translationgroup) REFERENCES public.translationgroup(id);


ALTER TABLE ONLY public.usertouseremail
    ADD CONSTRAINT usertouseremail__recipient__fk FOREIGN KEY (recipient) REFERENCES public.person(id);


ALTER TABLE ONLY public.usertouseremail
    ADD CONSTRAINT usertouseremail__sender__fk FOREIGN KEY (sender) REFERENCES public.person(id);


ALTER TABLE ONLY public.vote
    ADD CONSTRAINT vote_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.vote
    ADD CONSTRAINT vote_poll_fk FOREIGN KEY (poll) REFERENCES public.poll(id);


ALTER TABLE ONLY public.vote
    ADD CONSTRAINT vote_poll_option_fk FOREIGN KEY (poll, option) REFERENCES public.polloption(poll, id);


ALTER TABLE ONLY public.votecast
    ADD CONSTRAINT votecast_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.votecast
    ADD CONSTRAINT votecast_poll_fk FOREIGN KEY (poll) REFERENCES public.poll(id);


ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT webhook_branch_fkey FOREIGN KEY (branch) REFERENCES public.branch(id);


ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT webhook_git_repository_fkey FOREIGN KEY (git_repository) REFERENCES public.gitrepository(id);


ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT webhook_registrant_fkey FOREIGN KEY (registrant) REFERENCES public.person(id);


ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT webhook_snap_fkey FOREIGN KEY (snap) REFERENCES public.snap(id);


ALTER TABLE ONLY public.webhookjob
    ADD CONSTRAINT webhookjob_job_fkey FOREIGN KEY (job) REFERENCES public.job(id) ON DELETE CASCADE;


ALTER TABLE ONLY public.webhookjob
    ADD CONSTRAINT webhookjob_webhook_fkey FOREIGN KEY (webhook) REFERENCES public.webhook(id);


ALTER TABLE ONLY public.wikiname
    ADD CONSTRAINT wikiname_person_fk FOREIGN KEY (person) REFERENCES public.person(id);


ALTER TABLE ONLY public.xref
    ADD CONSTRAINT xref_creator_fkey FOREIGN KEY (creator) REFERENCES public.person(id);




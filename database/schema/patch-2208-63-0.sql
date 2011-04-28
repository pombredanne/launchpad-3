-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE BugSummary(
    id serial PRIMARY KEY,
    count INTEGER NOT NULL default 0,
    product INTEGER REFERENCES Product ON DELETE CASCADE,
    productseries INTEGER REFERENCES ProductSeries ON DELETE CASCADE,
    distribution INTEGER REFERENCES Distribution ON DELETE CASCADE,
    distroseries INTEGER REFERENCES DistroSeries ON DELETE CASCADE,
    sourcepackagename INTEGER REFERENCES SourcePackageName ON DELETE CASCADE,
    viewed_by INTEGER REFERENCES Person ON DELETE CASCADE,
    tag TEXT,
    status INTEGER NOT NULL,
    milestone INTEGER REFERENCES Milestone ON DELETE CASCADE,
    CONSTRAINT bugtask_assignment_checks CHECK (
        CASE
            WHEN product IS NOT NULL THEN
                productseries IS NULL
                AND distribution IS NULL
                AND distroseries IS NULL
                AND sourcepackagename IS NULL
            WHEN productseries IS NOT NULL THEN
                distribution IS NULL
                AND distroseries IS NULL
                AND sourcepackagename IS NULL
            WHEN distribution IS NOT NULL THEN
                distroseries IS NULL
            WHEN distroseries IS NOT NULL THEN
                TRUE
            ELSE
                FALSE
        END)
);

---- Bulk load into the table - after this it is maintained by trigger. Timed
-- at 2-3 minutes on staging.
-- basic theory: each bug *task* has some unary dimensions (like status) and
-- some N-ary dimensions (like contexts [sourcepackage+distro, distro only], or
-- subscriptions, or tags). For N-ary dimensions we record the bug against all
-- positions in that dimension.
-- Some tasks aggregate into the same dimension - e.g. two different source
-- packages tasks in Ubuntu. At the time of writing we only want to count those
-- once ( because we have had user confusion when two tasks of the same bug are
-- both counted toward portal aggregates). So we add bug.id distinct.
-- We don't map INCOMPLETE to INCOMPLETE_WITH_RESPONSE - instead we'll let that
-- migration happen separately.
-- So the rules the code below should be implementing are:
-- once for each task in a different target
-- once for each subscription (private bugs) (left join subscribers conditionally on privacy)
-- once for each sourcepackage name + one with sourcepackagename=NULL (two queries unioned)
-- once for each tag + one with tag=NULL (two queries unioned)
-- bugs with duplicateof non null are excluded because we exclude them from all our aggregates.
INSERT INTO bugsummary (
    count, product, productseries, distribution, distroseries,
    sourcepackagename, viewed_by, tag, status, milestone)
WITH
    -- kill dupes
    relevant_bug AS (SELECT * FROM bug where duplicateof is NULL),

    -- (bug.id, tag) for all bug-tag pairs plus (bug.id, NULL) for all bugs
    bug_tags AS (
        SELECT relevant_bug.id, NULL::text AS tag FROM relevant_bug
        UNION
        SELECT relevant_bug.id, tag
        FROM relevant_bug INNER JOIN bugtag ON relevant_bug.id=bugtag.bug),
    -- (bug.id, NULL) for all public bugs + (bug.id, viewer) for all
    -- (subscribers+assignee) on private bugs
    bug_viewers AS (
        SELECT relevant_bug.id, NULL::integer AS person
        FROM relevant_bug WHERE NOT relevant_bug.private
        UNION
        SELECT relevant_bug.id, assignee AS person
        FROM relevant_bug
        INNER JOIN bugtask ON relevant_bug.id=bugtask.bug
        WHERE relevant_bug.private and bugtask.assignee IS NOT NULL
        UNION
        SELECT relevant_bug.id, bugsubscription.person
        FROM relevant_bug INNER JOIN bugsubscription
            ON bugsubscription.bug=relevant_bug.id WHERE relevant_bug.private),

    -- (bugtask.(bug, product, productseries, distribution, distroseries,
    -- sourcepackagename, status, milestone) for all bugs + the same with
    -- sourcepackage squashed to NULL)
    tasks AS (
        SELECT
            bug, product, productseries, distribution, distroseries,
            sourcepackagename, status, milestone
        FROM bugtask
        UNION
        SELECT DISTINCT ON (
            bug, product, productseries, distribution, distroseries,
            sourcepackagename, milestone)
            bug, product, productseries, distribution, distroseries,
            NULL::integer as sourcepackagename,
            status, milestone
        FROM bugtask where sourcepackagename IS NOT NULL)

    -- Now combine
    SELECT
        count(*), product, productseries, distribution, distroseries,
        sourcepackagename, person, tag, status, milestone
    FROM relevant_bug
    INNER JOIN bug_tags ON relevant_bug.id=bug_tags.id
    INNER JOIN bug_viewers ON relevant_bug.id=bug_viewers.id
    INNER JOIN tasks on tasks.bug=relevant_bug.id
    GROUP BY
        product, productseries, distribution, distroseries,
        sourcepackagename, person, tag, status, milestone;

-- XXX: Is there a reason why the distribution, distroseries, product
-- and productseries indexes are not partial?
-- Need indices for FK CASCADE DELETE to find any FK easily
CREATE INDEX bugsummary_distribution on bugsummary using btree(distribution);
CREATE INDEX bugsummary_distroseries on bugsummary using btree(distroseries);
CREATE INDEX bugsummary_privates on bugsummary using btree(viewed_by) where viewed_by is not null;
CREATE INDEX bugsummary_product on bugsummary using btree(product);
CREATE INDEX bugsummary_productseries on bugsummary using btree(productseries);
-- can only have one fact row per set of dimensions
CREATE UNIQUE INDEX bugsummary_dimensions_unique_idx ON bugsummary USING btree (
    COALESCE(product, (-1)),
    COALESCE(productseries, (-1)),
    COALESCE(distribution, (-1)),
    COALESCE(distroseries, (-1)),
    COALESCE(sourcepackagename, (-1)),
    COALESCE(viewed_by, (-1)),
    COALESCE(tag, ('')),
    status,
    COALESCE(milestone, (-1)));
-- While querying is tolerably fast with the base dimension indices, we want snappy:
-- Distribution bug counts
CREATE INDEX bugsummary_distribution_count_idx on bugsummary using btree(distribution) where sourcepackagename is null and tag is null;
-- Distribution wide tag counts
CREATE INDEX bugsummary_distribution_tag_count_idx on bugsummary using btree(distribution) where sourcepackagename is null and tag is not null;
-- Everything (counts)
-- XXX: What is this index used for? Looks like counts of bugs with a given
-- status
CREATE INDEX bugsummary_count_idx on bugsummary using btree(status) where sourcepackagename is null and tag is null;
-- Everything (tags)
CREATE INDEX bugsummary_tag_count_idx on bugsummary using btree(status) where sourcepackagename is null and tag is not null;





--
-- Functions temporary exist here.
-- They can't go in trusted.sql at the moment, because trusted.sql is
-- run against an empty database. If these functions where in there,
-- it would fail because they use BugSummary table as a useful
-- composite type.
-- I suspect we will need to leave these function definitions in here,
-- and move them to trusted.sql after the baseline SQL script contains
-- the BugSummary table definition.
--

CREATE OR REPLACE FUNCTION bug_summary_inc(d bugsummary) RETURNS VOID
LANGUAGE plpgsql AS
$$
BEGIN
    -- Shameless adaption from postgresql manual
    LOOP
        -- first try to update the row
        UPDATE BugSummary SET count = count + 1
        WHERE
            product IS NOT DISTINCT FROM d.product
            AND productseries IS NOT DISTINCT FROM d.productseries
            AND distribution IS NOT DISTINCT FROM d.distribution
            AND distroseries IS NOT DISTINCT FROM d.distroseries
            AND sourcepackagename IS NOT DISTINCT FROM d.sourcepackagename
            AND viewed_by IS NOT DISTINCT FROM d.viewed_by
            AND tag IS NOT DISTINCT FROM d.tag
            AND status IS NOT DISTINCT FROM d.status
            AND milestone IS NOT DISTINCT FROM d.milestone;
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
                status, milestone)
            VALUES (
                1, d.product, d.productseries, d.distribution,
                d.distroseries, d.sourcepackagename, d.viewed_by, d.tag,
                d.status, d.milestone);
            RETURN;
        EXCEPTION WHEN unique_violation THEN
            -- do nothing, and loop to try the UPDATE again
        END;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION bug_summary_inc(bugsummary) IS
'UPSERT into bugsummary incrementing one row';

CREATE OR REPLACE FUNCTION bug_summary_dec(d bugsummary) RETURNS VOID
LANGUAGE plpgsql AS
$$
BEGIN
    -- We own the row reference, so in the absence of bugs this cannot
    -- fail - just decrement the row.
    UPDATE BugSummary SET count = count - 1
    WHERE
        product IS NOT DISTINCT FROM d.product
        AND productseries IS NOT DISTINCT FROM d.productseries
        AND distribution IS NOT DISTINCT FROM d.distribution
        AND distroseries IS NOT DISTINCT FROM d.distroseries
        AND sourcepackagename IS NOT DISTINCT FROM d.sourcepackagename
        AND viewed_by IS NOT DISTINCT FROM d.viewed_by
        AND tag IS NOT DISTINCT FROM d.tag
        AND status IS NOT DISTINCT FROM d.status
        AND milestone IS NOT DISTINCT FROM d.milestone;
    -- gc the row (perhaps should be garbo but easy enough to add here:
    DELETE FROM bugsummary
    WHERE
        count=0
        AND product IS NOT DISTINCT FROM d.product
        AND productseries IS NOT DISTINCT FROM d.productseries
        AND distribution IS NOT DISTINCT FROM d.distribution
        AND distroseries IS NOT DISTINCT FROM d.distroseries
        AND sourcepackagename IS NOT DISTINCT FROM d.sourcepackagename
        AND viewed_by IS NOT DISTINCT FROM d.viewed_by
        AND tag IS NOT DISTINCT FROM d.tag
        AND status IS NOT DISTINCT FROM d.status
        AND milestone IS NOT DISTINCT FROM d.milestone;
    -- If its not found then someone else also dec'd and won concurrently.
END;
$$;

COMMENT ON FUNCTION bug_summary_inc(bugsummary) IS
'UPSERT into bugsummary incrementing one row';


CREATE OR REPLACE FUNCTION bugsummary_viewers(BUG_ROW bug)
RETURNS SETOF bugsubscription LANGUAGE SQL STABLE AS
$$
    SELECT *
    FROM BugSubscription
    WHERE
        bugsubscription.bug=$1.id
        AND $1.private IS TRUE;
$$;

COMMENT ON FUNCTION bugsummary_viewers(bug) IS
'Return (bug, viewer) for all viewers if private, nothing otherwise';


CREATE OR REPLACE FUNCTION bugsummary_tags(BUG_ROW bug)
RETURNS SETOF bugtag LANGUAGE SQL STABLE AS
$$
    SELECT * FROM BugTag WHERE BugTag.bug = $1.id
    UNION ALL
    SELECT NULL AS id, $1.id AS bug, NULL AS tag;
$$;

COMMENT ON FUNCTION bugsummary_tags(bug) IS
'Return (bug, tag) for all tags + (bug, NULL::text)';


CREATE OR REPLACE FUNCTION bugsummary_tasks(bug_id integer)
RETURNS SETOF bugtask LANGUAGE plpgsql STABLE AS
$$
DECLARE
    r bugtask%ROWTYPE;
BEGIN
    -- One row only for each target permutation - need to ignore other fields
    -- like date last modified to deal with conjoined masters and multiple
    -- sourcepackage tasks in a distro.
    FOR r IN
        SELECT
            bug, product, productseries, distribution, distroseries,
            sourcepackagename, status, milestone
        FROM BugTask WHERE bug=bug_id
        UNION
        SELECT
            bug, product, productseries, distribution, distroseries,
            NULL, status, milestone
        FROM BugTask WHERE bug=bug_id AND sourcepackagename IS NOT NULL
    LOOP
        RETURN NEXT r;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION bugsummary_tasks(bug) IS
'Return all tasks for the bug + all sourcepackagename tasks again with the sourcepackagename squashed';



CREATE OR REPLACE FUNCTION bugsummary_locations(BUG_ROW bug)
RETURNS SETOF bugsummary LANGUAGE plpgsql AS
$$
DECLARE
    r bugsummary%ROWTYPE;
    tags bugtag%ROWTYPE;
BEGIN
    IF bug.duplicateof THEN
        RETURN;
    END IF;
    -- gets tag coordinates
    tags = SELECT * FROM bugsummary_tags(bug);
    viewers = SELECT * FROM bugsummary_viewers(bug);
    tasks = SELECT * FROM bugsummary_tasks(bug);
    /* next step - turn this old aggregate into a combo of the above three function results as a setof rows rather than a counted result - because it may be incrementing or decrementing */
    SELECT
        count(*), product, productseries, distribution, distroseries,
        sourcepackagename, person, tag, status, milestone
    FROM relevant_bug
    INNER JOIN bug_tags ON relevant_bug.id=bug_tags.id
    INNER JOIN bug_viewers ON relevant_bug.id=bug_viewers.id
    INNER JOIN tasks on tasks.bug=relevant_bug.id
    GROUP BY
        product, productseries, distribution, distroseries,
        sourcepackagename, person, tag, status, milestone;

    -- 
    r.product = 1; -- XXX: Fill in with real data.
    RETURN NEXT r;
    r.product = NULL;
    r.productseries = 1;
    RETURN NEXT r;
END;
$$;

COMMENT ON FUNCTION bugsummary_locations(int) IS
'Calculate what BugSummary rows should exist for a given Bug.';


CREATE OR REPLACE FUNCTION summarise_bug(BUG_ROW bug) RETURNS VOID
LANGUAGE plpgsql VOLATILE AS
$$
DECLARE
    d bugsummary%ROWTYPE;
BEGIN
    FOR d IN SELECT * FROM bugsummary_locations(BUG_ROW) LOOP
        PERFORM bug_summary_inc(d);
    END LOOP;
END;
$$;

COMMENT ON FUNCTION summarise_bug(int) IS
'AFTER summarise a bug row into bugsummary.';

/*
CREATE OR REPLACE FUNCTION unsummarise_bug(BUG_ROW bug) RETURNS VOID
LANGUAGE plpgsql VOLATILE AS
$$
BEGIN
something like
for summary-address in SELECT(summary_locations(BUG_ROW)
    bug_summary_dec(summary-address);

END;
$$;

COMMENT ON FUNCTION unsummarise_bug(bug) IS
'AFTER unsummarise a bug row from bugsummary.';
*/


CREATE OR REPLACE FUNCTION bug_maintain_bug_summary() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE AS
$$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.duplicateof IS NOT NULL and OLD.duplicateof IS NOT NULL THEN
            -- Duplicates are not summarised
            RETURN NULL; -- Ignored - this is an AFTER trigger
        END IF;
        IF NEW.duplicateof = OLD.duplicateof AND 
           NEW.private = OLD.private THEN
            -- Short circuit on an update that doesn't change inclusion or
            -- summary logic
            RETURN NULL; -- Ignored - this is an AFTER trigger
        END IF;
        IF OLD.duplicateof IS NOT NULL THEN
            -- Newly unduplicated: publish fresh
            SELECT summarise_bug(NEW);
        ELSIF NEW.duplicateof IS NOT NULL THEN
            -- Newly duplicated: unsummarise
            SELECT unsummarise_bug(OLD);
        ELSIF NEW.private = OLD.private THEN
            -- Not changed in a relevant way, we're done.
            RETURN NULL; -- Ignored - this is an AFTER trigger
        ELSE
            -- Either becoming private or public; none of the summary rows are
            -- in common - remove and add.
            SELECT unsummarise_bug(OLD);
            SELECT summarise_bug(NEW);
        END IF;
        RETURN NULL; -- Ignored - this is an AFTER trigger
    END IF;

    -- For delete remove the bugs summary rows
    SELECT unsummarise_bug(OLD);
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION bug_maintain_bug_summary() IS
'AFTER trigger on bug maintaining the bugs summaries in bugsummary.';

/*
CREATE OR REPLACE FUNCTION bugtask_maintain_bug_summary() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE AS
$$
BEGIN
    if the target changes needs to dec all the rows for the old target and inc for the new target. 
    special mention:
       the counting of /bugs/ once at distribution/distroseris scope even if they have many sourcepackage tasks means that this needs to cooperate with the bug - when decrementing rows if any other task also qualifies for the matching distroseries/distribution aggregate, don't alter it - it was only counted once.
    milestone changes are easy - just multiple out by subscribers and tags , dev the old milestone value inc the new
    status changes likewise
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION bugtask_maintain_bug_summary() IS
'AFTER trigger on bugtask maintaining the bugs summaries in bugsummary.';

CREATE OR REPLACE FUNCTION bugsubscription_maintain_bug_summary() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE AS
$$
BEGIN
    if the bug is public this is a noop 
        otherwise take the public summary locations and inc/dec each location with the subscriber person as the viewed_by 
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION bugsubscription_maintain_bug_summary() IS
'AFTER trigger on bugsubscription maintaining the bugs summaries in bugsummary.';

CREATE OR REPLACE FUNCTION bugtag_maintain_bug_summary() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE AS
$$
BEGIN
    similar to sourcepackages, tags have two cases:
     - all bugs are recorded against tag is NULL
     - bugs with tags are additionally recorded against each tag (cross-product multiply with all the other fields)
     
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION bugtag_maintain_bug_summary() IS
'AFTER trigger on bugtag maintaining the bugs summaries in bugsummary.';








-- we need to maintain the summaries when things change. Each variable the
-- population script above uses needs to be accounted for.

-- bug: duplicateof, private (not INSERT because a task is needed to be included in summaries.
CREATE TRIGGER bug_maintain_bug_summary_trigger AFTER UPDATE OR DELETE ON bug FOR EACH ROW EXECUTE PROCEDURE bug_maintain_bug_summary();
-- bugtask: target, status, milestone
CREATE TRIGGER bugtask_maintain_bug_summary_trigger AFTER INSERT OR UPDATE OR DELETE ON bugtask FOR EACH ROW EXECUTE PROCEDURE bugtask_maintain_bug_summary();
-- bugsubscription: existence
CREATE TRIGGER bugsubscription_maintain_bug_summary_trigger AFTER INSERT OR UPDATE OR DELETE ON bugsubscription FOR EACH ROW EXECUTE PROCEDURE bugsubscription_maintain_bug_summary();
-- bugtag: existence
CREATE TRIGGER bugtag_maintain_bug_summary_trigger AFTER INSERT OR UPDATE OR DELETE ON bugtag FOR EACH ROW EXECUTE PROCEDURE bugtag_maintain_bug_summary();

*/

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 63, 0);

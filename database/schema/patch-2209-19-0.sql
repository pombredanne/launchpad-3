-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Journal functions. Speed is critical -- these are run by appservers.

CREATE OR REPLACE FUNCTION public.bug_summary_flush_temp_journal()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    d bugsummary%ROWTYPE;
BEGIN
    -- may get called even though no summaries were made (for simplicity in the
    -- callers)
    PERFORM ensure_bugsummary_temp_journal();
    INSERT INTO BugSummaryJournal(
        count, product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone, importance, has_patch, fixed_upstream)
    SELECT
        count, product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone, importance, has_patch, fixed_upstream
        FROM bugsummary_temp_journal;
    TRUNCATE bugsummary_temp_journal;
END;
$function$;

CREATE OR REPLACE FUNCTION bugsummary_journal_bug(bug_row bug, _count integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
    PERFORM ensure_bugsummary_temp_journal();
    INSERT INTO BugSummary_Temp_Journal(
        count, product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone, importance, has_patch, fixed_upstream)
    SELECT
        _count, product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone, importance, has_patch, fixed_upstream
        FROM bugsummary_locations(BUG_ROW);
END;
$function$;

CREATE OR REPLACE FUNCTION public.bugsubscription_maintain_bug_summary()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO public
AS $function$
BEGIN
    -- This trigger only works if we are inserting, updating or deleting
    -- a single row per statement.
    IF TG_OP = 'INSERT' THEN
        IF (bug_row(NEW.bug)).information_type IN (1, 2) THEN
            -- Public subscriptions are not aggregated.
            RETURN NEW;
        END IF;
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(bug_row(NEW.bug));
        ELSE
            PERFORM summarise_bug(bug_row(NEW.bug));
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        IF (bug_row(OLD.bug)).information_type IN (1, 2) THEN
            -- Public subscriptions are not aggregated.
            RETURN OLD;
        END IF;
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(bug_row(OLD.bug));
        ELSE
            PERFORM summarise_bug(bug_row(OLD.bug));
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN OLD;
    ELSE
        IF (OLD.person IS DISTINCT FROM NEW.person
            OR OLD.bug IS DISTINCT FROM NEW.bug) THEN
            IF TG_WHEN = 'BEFORE' THEN
                IF (bug_row(OLD.bug)).information_type IN (3, 4, 5) THEN
                    -- Public subscriptions are not aggregated.
                    PERFORM unsummarise_bug(bug_row(OLD.bug));
                END IF;
                IF OLD.bug <> NEW.bug AND (bug_row(NEW.bug)).information_type IN (3, 4, 5) THEN
                    -- Public subscriptions are not aggregated.
                    PERFORM unsummarise_bug(bug_row(NEW.bug));
                END IF;
            ELSE
                IF (bug_row(OLD.bug)).information_type IN (3, 4, 5) THEN
                    -- Public subscriptions are not aggregated.
                    PERFORM summarise_bug(bug_row(OLD.bug));
                END IF;
                IF OLD.bug <> NEW.bug AND (bug_row(NEW.bug)).information_type IN (3, 4, 5) THEN
                    -- Public subscriptions are not aggregated.
                    PERFORM summarise_bug(bug_row(NEW.bug));
                END IF;
            END IF;
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN NEW;
    END IF;
END;
$function$;

CREATE OR REPLACE FUNCTION public.bugsummary_locations(bug_row bug)
 RETURNS SETOF bugsummary
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF BUG_ROW.duplicateof IS NOT NULL THEN
        RETURN;
    END IF;
    RETURN QUERY
        SELECT
            CAST(NULL AS integer) AS id,
            CAST(1 AS integer) AS count,
            product, productseries, distribution, distroseries,
            sourcepackagename, person AS viewed_by, tag, status, milestone,
            importance,
            BUG_ROW.latest_patch_uploaded IS NOT NULL AS has_patch,
            (EXISTS (
                SELECT TRUE FROM BugTask AS RBT
                WHERE
                    RBT.bug = tasks.bug
                    -- This would just be 'RBT.id <> tasks.id', except
                    -- that the records from tasks are summaries and not
                    -- real bugtasks, and do not have an id.
                    AND (RBT.product IS DISTINCT FROM tasks.product
                        OR RBT.productseries
                            IS DISTINCT FROM tasks.productseries
                        OR RBT.distribution IS DISTINCT FROM tasks.distribution
                        OR RBT.distroseries IS DISTINCT FROM tasks.distroseries
                        OR RBT.sourcepackagename
                            IS DISTINCT FROM tasks.sourcepackagename)
                    -- Flagged as INVALID, FIXCOMMITTED or FIXRELEASED
                    -- via a bugwatch, or FIXCOMMITTED or FIXRELEASED on
                    -- the product.
                    AND ((bugwatch IS NOT NULL AND status IN (17, 25, 30))
                        OR (bugwatch IS NULL AND product IS NOT NULL
                            AND status IN (25, 30))))
                )::boolean AS fixed_upstream
        FROM bugsummary_tasks(BUG_ROW) AS tasks
        JOIN bugsummary_tags(BUG_ROW) AS bug_tags ON TRUE
        LEFT OUTER JOIN bugsummary_viewers(BUG_ROW) AS bug_viewers ON TRUE;
END;
$function$;

CREATE OR REPLACE FUNCTION public.bugsummary_tags(bug_row bug)
 RETURNS SETOF bugtag
 LANGUAGE sql
 STABLE
AS $function$
    SELECT * FROM BugTag WHERE BugTag.bug = $1.id
    UNION ALL
    SELECT NULL::integer, $1.id, NULL::text;
$function$;

CREATE OR REPLACE FUNCTION public.bugsummary_tasks(bug_row bug)
 RETURNS SETOF bugtask
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    bt bugtask%ROWTYPE;
    r record;
BEGIN
    bt.bug = BUG_ROW.id;

    -- One row only for each target permutation - need to ignore other fields
    -- like date last modified to deal with conjoined masters and multiple
    -- sourcepackage tasks in a distro.
    FOR r IN
        SELECT
            product, productseries, distribution, distroseries,
            sourcepackagename, status, milestone, importance, bugwatch
        FROM BugTask WHERE bug=BUG_ROW.id
        UNION -- Implicit DISTINCT
        SELECT
            product, productseries, distribution, distroseries,
            NULL, status, milestone, importance, bugwatch
        FROM BugTask WHERE bug=BUG_ROW.id AND sourcepackagename IS NOT NULL
    LOOP
        bt.product = r.product;
        bt.productseries = r.productseries;
        bt.distribution = r.distribution;
        bt.distroseries = r.distroseries;
        bt.sourcepackagename = r.sourcepackagename;
        bt.status = r.status;
        bt.milestone = r.milestone;
        bt.importance = r.importance;
        bt.bugwatch = r.bugwatch;
        RETURN NEXT bt;
    END LOOP;
END;
$function$;

CREATE OR REPLACE FUNCTION public.bugsummary_viewers(bug_row bug)
 RETURNS SETOF bugsubscription
 LANGUAGE sql
 STABLE
AS $function$
    SELECT *
    FROM BugSubscription
    WHERE
        bugsubscription.bug=$1.id
        AND $1.information_type IN (3, 4, 5);
$function$;

CREATE OR REPLACE FUNCTION public.bugtag_maintain_bug_summary()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO public
AS $function$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(bug_row(NEW.bug));
        ELSE
            PERFORM summarise_bug(bug_row(NEW.bug));
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(bug_row(OLD.bug));
        ELSE
            PERFORM summarise_bug(bug_row(OLD.bug));
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN OLD;
    ELSE
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(bug_row(OLD.bug));
            IF OLD.bug <> NEW.bug THEN
                PERFORM unsummarise_bug(bug_row(NEW.bug));
            END IF;
        ELSE
            PERFORM summarise_bug(bug_row(OLD.bug));
            IF OLD.bug <> NEW.bug THEN
                PERFORM summarise_bug(bug_row(NEW.bug));
            END IF;
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN NEW;
    END IF;
END;
$function$;

CREATE OR REPLACE FUNCTION public.bugtask_maintain_bug_summary()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO public
AS $function$
BEGIN
    -- This trigger only works if we are inserting, updating or deleting
    -- a single row per statement.

    -- Unlike bug_maintain_bug_summary, this trigger does not have access
    -- to the old bug when invoked as an AFTER trigger. To work around this
    -- we install this trigger as both a BEFORE and an AFTER trigger.
    IF TG_OP = 'INSERT' THEN
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(bug_row(NEW.bug));
        ELSE
            PERFORM summarise_bug(bug_row(NEW.bug));
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(bug_row(OLD.bug));
        ELSE
            PERFORM summarise_bug(bug_row(OLD.bug));
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN OLD;

    ELSE
        IF (OLD.product IS DISTINCT FROM NEW.product
            OR OLD.productseries IS DISTINCT FROM NEW.productseries
            OR OLD.distribution IS DISTINCT FROM NEW.distribution
            OR OLD.distroseries IS DISTINCT FROM NEW.distroseries
            OR OLD.sourcepackagename IS DISTINCT FROM NEW.sourcepackagename
            OR OLD.status IS DISTINCT FROM NEW.status
            OR OLD.importance IS DISTINCT FROM NEW.importance
            OR OLD.bugwatch IS DISTINCT FROM NEW.bugwatch
            OR OLD.milestone IS DISTINCT FROM NEW.milestone) THEN

            IF TG_WHEN = 'BEFORE' THEN
                PERFORM unsummarise_bug(bug_row(OLD.bug));
                IF OLD.bug <> NEW.bug THEN
                    PERFORM unsummarise_bug(bug_row(NEW.bug));
                END IF;
            ELSE
                PERFORM summarise_bug(bug_row(OLD.bug));
                IF OLD.bug <> NEW.bug THEN
                    PERFORM summarise_bug(bug_row(NEW.bug));
                END IF;
            END IF;
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN NEW;
    END IF;
END;
$function$;

CREATE OR REPLACE FUNCTION public.ensure_bugsummary_temp_journal()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
BEGIN
    CREATE TEMPORARY TABLE bugsummary_temp_journal (
        LIKE bugsummary ) ON COMMIT DROP;
    ALTER TABLE bugsummary_temp_journal ALTER COLUMN id DROP NOT NULL;
EXCEPTION
    WHEN duplicate_table THEN
        NULL;
END;
$function$;

CREATE OR REPLACE FUNCTION public.summarise_bug(bug_row bug)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
    PERFORM bugsummary_journal_bug(bug_row, 1);
END;
$function$;

CREATE OR REPLACE FUNCTION public.unsummarise_bug(bug_row bug)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
    PERFORM bugsummary_journal_bug(bug_row, -1);
END;
$function$;


-- Rollup functions. Speed isn't critical, as it's done post-request by garbo.

CREATE OR REPLACE FUNCTION public.bugsummary_rollup_journal(batchsize integer DEFAULT NULL::integer)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO public
AS $function$
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
            fixed_upstream
        FROM BugSummaryJournal
        WHERE id <= max_id
        GROUP BY
            product, productseries, distribution, distroseries,
            sourcepackagename, viewed_by, tag, status, milestone,
            importance, has_patch, fixed_upstream
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
$function$;


CREATE OR REPLACE FUNCTION public.bug_summary_inc(d bugsummary)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
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
            AND fixed_upstream = $1.fixed_upstream;
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
                status, milestone,
                importance, has_patch, fixed_upstream)
            VALUES (
                d.count, d.product, d.productseries, d.distribution,
                d.distroseries, d.sourcepackagename, d.viewed_by, d.tag,
                d.status, d.milestone,
                d.importance, d.has_patch, d.fixed_upstream);
            RETURN;
        EXCEPTION WHEN unique_violation THEN
            -- do nothing, and loop to try the UPDATE again
        END;
    END LOOP;
END;
$function$;

CREATE OR REPLACE FUNCTION public.bug_summary_dec(bugsummary)
 RETURNS void
 LANGUAGE sql
AS $function$
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
        AND fixed_upstream = $1.fixed_upstream;
$function$;

DROP FUNCTION bug_summary_temp_journal_ins(bugsummary);
DROP FUNCTION bugsummary_journal_ins(bugsummary);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 19, 0);

-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- bad comment fixup
COMMENT ON FUNCTION bug_summary_dec(bugsummary) IS
'UPSERT into bugsummary incrementing one row';

CREATE OR REPLACE FUNCTION ensure_bugsummary_temp_journal() RETURNS VOID
LANGUAGE plpgsql VOLATILE AS
$$
DECLARE
BEGIN
    CREATE TEMPORARY TABLE bugsummary_temp_journal (
        LIKE bugsummary ) ON COMMIT DROP;
    ALTER TABLE bugsummary_temp_journal ALTER COLUMN id DROP NOT NULL;
    -- For safety use a unique index.
    CREATE UNIQUE INDEX bugsummary__temp_journal__dimensions__unique ON bugsummary_temp_journal (
        status,
        COALESCE(product, (-1)),
        COALESCE(productseries, (-1)),
        COALESCE(distribution, (-1)),
        COALESCE(distroseries, (-1)),
        COALESCE(sourcepackagename, (-1)),
        COALESCE(viewed_by, (-1)),
        COALESCE(milestone, (-1)),
        COALESCE(tag, ('')));
EXCEPTION
    WHEN duplicate_table THEN
        NULL;
END;
$$;

COMMENT ON FUNCTION ensure_bugsummary_temp_journal() IS
'Create a temporary table bugsummary_temp_journal if it does not exist.';

CREATE OR REPLACE FUNCTION bug_summary_temp_journal_clean_row(d bugsummary) RETURNS VOID
LANGUAGE plpgsql AS
$$
BEGIN
    -- maybe gc the row (perhaps should be garbo but easy enough to add here:
    DELETE FROM bugsummary_temp_journal
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
END;
$$;

COMMENT ON FUNCTION bug_summary_temp_journal_clean_row(bugsummary) IS
'Remove a row from the temp journal if its count is 0';

CREATE OR REPLACE FUNCTION bug_summary_temp_journal_dec(d bugsummary) RETURNS VOID
LANGUAGE plpgsql AS
$$
BEGIN
    -- We own the row reference, so in the absence of bugs this cannot
    -- fail - just decrement the row.
    UPDATE BugSummary_Temp_Journal SET count = count - 1
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
        PERFORM bug_summary_temp_journal_clean_row(d);
        RETURN;
    END IF;
    -- not there, so try to insert the key
    INSERT INTO BugSummary_Temp_Journal(
        count, product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone)
    VALUES (
        -1, d.product, d.productseries, d.distribution,
        d.distroseries, d.sourcepackagename, d.viewed_by, d.tag,
        d.status, d.milestone);
    RETURN;
END;
$$;

COMMENT ON FUNCTION bug_summary_temp_journal_dec(bugsummary) IS
'UPSERT into bugsummary_temp_journal decrementing one row';

CREATE OR REPLACE FUNCTION bug_summary_temp_journal_inc(d bugsummary) RETURNS VOID
LANGUAGE plpgsql AS
$$
BEGIN
    -- first try to update the row
    UPDATE BugSummary_Temp_Journal SET count = count + 1
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
        PERFORM bug_summary_temp_journal_clean_row($1);
        RETURN;
    END IF;
    -- not there, so try to insert the key
    INSERT INTO BugSummary_Temp_Journal(
        count, product, productseries, distribution,
        distroseries, sourcepackagename, viewed_by, tag,
        status, milestone)
    VALUES (
        1, d.product, d.productseries, d.distribution,
        d.distroseries, d.sourcepackagename, d.viewed_by, d.tag,
        d.status, d.milestone);
    RETURN;
END;
$$;

COMMENT ON FUNCTION bug_summary_temp_journal_inc(bugsummary) IS
'UPSERT into bugsummary incrementing one row';

CREATE OR REPLACE FUNCTION bug_summary_flush_temp_journal() RETURNS VOID
LANGUAGE plpgsql VOLATILE AS
$$
DECLARE
    d bugsummary%ROWTYPE;
BEGIN
    -- may get called even though no summaries were made (for simplicity in the
    -- callers)
    PERFORM ensure_bugsummary_temp_journal();
    FOR d IN SELECT * FROM bugsummary_temp_journal LOOP
        IF d.count < 0 THEN
            PERFORM bug_summary_dec(d);
        ELSIF d.count > 0 THEN
            PERFORM bug_summary_inc(d);
        END IF;
    END LOOP;
    DELETE FROM bugsummary_temp_journal;
END;
$$;

COMMENT ON FUNCTION bug_summary_flush_temp_journal() IS
'flush the temporary bugsummary journal into the bugsummary table';

CREATE OR REPLACE FUNCTION unsummarise_bug(BUG_ROW bug) RETURNS VOID
LANGUAGE plpgsql VOLATILE AS
$$
DECLARE
    d bugsummary%ROWTYPE;
BEGIN
    PERFORM ensure_bugsummary_temp_journal();
    FOR d IN SELECT * FROM bugsummary_locations(BUG_ROW) LOOP
        PERFORM bug_summary_temp_journal_dec(d);
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION summarise_bug(BUG_ROW bug) RETURNS VOID
LANGUAGE plpgsql VOLATILE AS
$$
DECLARE
    d bugsummary%ROWTYPE;
BEGIN
    PERFORM ensure_bugsummary_temp_journal();
    FOR d IN SELECT * FROM bugsummary_locations(BUG_ROW) LOOP
        PERFORM bug_summary_temp_journal_inc(d);
    END LOOP;
END;
$$;

-- fixed to summarise less often and use the journal.
CREATE OR REPLACE FUNCTION bugsubscription_maintain_bug_summary()
RETURNS TRIGGER LANGUAGE plpgsql VOLATILE
SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    -- This trigger only works if we are inserting, updating or deleting
    -- a single row per statement.
    IF TG_OP = 'INSERT' THEN
        IF NOT (bug_row(NEW.bug)).private THEN
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
        IF NOT (bug_row(OLD.bug)).private THEN
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
                IF (bug_row(OLD.bug)).private THEN
                    -- Public subscriptions are not aggregated.
                    PERFORM unsummarise_bug(bug_row(OLD.bug));
                END IF;
                IF OLD.bug <> NEW.bug AND (bug_row(NEW.bug)).private THEN
                    -- Public subscriptions are not aggregated.
                    PERFORM unsummarise_bug(bug_row(NEW.bug));
                END IF;
            ELSE
                IF (bug_row(OLD.bug)).private THEN
                    -- Public subscriptions are not aggregated.
                    PERFORM summarise_bug(bug_row(OLD.bug));
                END IF;
                IF OLD.bug <> NEW.bug AND (bug_row(NEW.bug)).private THEN
                    -- Public subscriptions are not aggregated.
                    PERFORM summarise_bug(bug_row(NEW.bug));
                END IF;
            END IF;
        END IF;
        PERFORM bug_summary_flush_temp_journal();
        RETURN NEW;
    END IF;
END;
$$;

-- fixed to use the journal
CREATE OR REPLACE FUNCTION bugtag_maintain_bug_summary() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
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
$$;

-- fixed to use the journal
CREATE OR REPLACE FUNCTION bug_maintain_bug_summary() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    -- There is no INSERT logic, as a bug will not have any summary
    -- information until BugTask rows have been attached.
    IF TG_OP = 'UPDATE' THEN
        IF OLD.duplicateof IS DISTINCT FROM NEW.duplicateof
            OR OLD.private IS DISTINCT FROM NEW.private THEN
            PERFORM unsummarise_bug(OLD);
            PERFORM summarise_bug(NEW);
        END IF;

    ELSIF TG_OP = 'DELETE' THEN
        PERFORM unsummarise_bug(OLD);
    END IF;

    PERFORM bug_summary_flush_temp_journal();
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

-- fixed to use the journal
CREATE OR REPLACE FUNCTION bugtask_maintain_bug_summary() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
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
$$;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 63, 1);

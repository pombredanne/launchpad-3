-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE OR REPLACE FUNCTION bugsummary_journal_ins(d bugsummary)
RETURNS VOID
LANGUAGE plpgsql AS
$$
BEGIN
    IF d.count <> 0 THEN
        INSERT INTO BugSummaryJournal (
            count, product, productseries, distribution,
            distroseries, sourcepackagename, viewed_by, tag,
            status, milestone)
        VALUES (
            d.count, d.product, d.productseries, d.distribution,
            d.distroseries, d.sourcepackagename, d.viewed_by, d.tag,
            d.status, d.milestone);
    END IF;
END;
$$;

COMMENT ON FUNCTION bugsummary_journal_ins(bugsummary) IS
'Add an entry into BugSummaryJournal';


CREATE OR REPLACE FUNCTION bugsummary_rollup_journal() RETURNS VOID
LANGUAGE plpgsql VOLATILE AS
$$
DECLARE
    d bugsummary%ROWTYPE;
    max_id integer;
BEGIN
    SELECT MAX(id) INTO max_id FROM BugSummaryJournal;

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
            milestone
        FROM BugSummaryJournal
        WHERE id <= max_id
        GROUP BY
            product, productseries, distribution, distroseries,
            sourcepackagename, viewed_by, tag, status, milestone
        HAVING sum(count) <> 0
    LOOP
        IF d.count < 0 THEN
            PERFORM bug_summary_dec(d);
        ELSIF d.count > 0 THEN
            PERFORM bug_summary_inc(d);
        END IF;
    END LOOP;

    DELETE FROM BugSummaryJournal WHERE id <= max_id;
END;
$$;

COMMENT ON FUNCTION bugsummary_rollup_journal() IS
'Collate and migrate rows from BugSummaryJournal to BugSummary';


CREATE OR REPLACE FUNCTION unsummarise_bug(BUG_ROW bug) RETURNS VOID
LANGUAGE plpgsql VOLATILE AS
$$
DECLARE
    d bugsummary%ROWTYPE;
BEGIN
    FOR d IN SELECT * FROM bugsummary_locations(BUG_ROW) LOOP
        d.count = -1;
        PERFORM bugsummary_journal_ins(d);
    END LOOP;
END;
$$;


CREATE OR REPLACE FUNCTION summarise_bug(BUG_ROW bug) RETURNS VOID
LANGUAGE plpgsql VOLATILE AS
$$
DECLARE
    d bugsummary%ROWTYPE;
BEGIN
    FOR d IN SELECT * FROM bugsummary_locations(BUG_ROW) LOOP
        d.count = 1;
        PERFORM bugsummary_journal_ins(d);
    END LOOP;
END;
$$;

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
        RETURN NEW;
    END IF;
END;
$$;


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
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(bug_row(OLD.bug));
        ELSE
            PERFORM summarise_bug(bug_row(OLD.bug));
        END IF;
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
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        IF TG_WHEN = 'BEFORE' THEN
            PERFORM unsummarise_bug(bug_row(OLD.bug));
        ELSE
            PERFORM summarise_bug(bug_row(OLD.bug));
        END IF;
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
        RETURN NEW;
    END IF;
END;
$$;

-- No longer needed - we have a persistent and replicated journal.
DROP FUNCTION ensure_bugsummary_temp_journal();
DROP FUNCTION bug_summary_flush_temp_journal();
DROP FUNCTION bug_summary_temp_journal_dec(d bugsummary);
DROP FUNCTION bug_summary_temp_journal_inc(d bugsummary);


INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 63, 4);

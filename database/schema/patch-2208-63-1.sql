-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;


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


INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 63, 1);

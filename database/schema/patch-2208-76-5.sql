SET client_min_messages TO ERROR;

-- Improve performance of this function by only doing the flush when
-- there have been relevant changes.

CREATE OR REPLACE FUNCTION bug_maintain_bug_summary() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
BEGIN
    -- There is no INSERT logic, as a bug will not have any summary
    -- information until BugTask rows have been attached.
    IF TG_OP = 'UPDATE' THEN
        IF OLD.duplicateof IS DISTINCT FROM NEW.duplicateof
            OR OLD.private IS DISTINCT FROM NEW.private
            OR (OLD.latest_patch_uploaded IS NULL)
                <> (NEW.latest_patch_uploaded IS NULL) THEN
            PERFORM unsummarise_bug(OLD);
            PERFORM summarise_bug(NEW);
            PERFORM bug_summary_flush_temp_journal();
        END IF;

    ELSIF TG_OP = 'DELETE' THEN
        PERFORM unsummarise_bug(OLD);
        PERFORM bug_summary_flush_temp_journal();
    END IF;

    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 76, 5);

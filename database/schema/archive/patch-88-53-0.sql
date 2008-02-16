SET client_min_messages=ERROR;

ALTER TABLE Bug
    ADD COLUMN message_count integer NOT NULL DEFAULT 0;

UPDATE Bug
SET message_count = (
    SELECT COUNT(BugMessage.id)
    FROM BugMessage
    WHERE BugMessage.bug = Bug.id);

CREATE TRIGGER set_bug_message_count_t
    AFTER INSERT OR DELETE OR UPDATE ON BugMessage
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_message_count();

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 53, 0);

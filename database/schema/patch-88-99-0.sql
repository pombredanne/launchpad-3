SET client_min_messages=ERROR;

ALTER TABLE Bug
    ADD COLUMN number_of_comments integer NOT NULL DEFAULT 0;

UPDATE Bug
SET number_of_comments = (
    SELECT COUNT(BugMessage.id)
    FROM BugMessage
    WHERE BugMessage.bug = Bug.id);

CREATE TRIGGER set_bug_number_of_comments_t
    AFTER INSERT OR DELETE ON BugMessage
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_number_of_comments();

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);

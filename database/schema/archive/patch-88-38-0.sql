SET client_min_messages=ERROR;

ALTER TABLE Bug
    ADD COLUMN number_of_duplicates integer NOT NULL DEFAULT 0;

UPDATE Bug
SET number_of_duplicates = (
    SELECT COUNT(Dup.id)
    FROM Bug as Dup
    WHERE Dup.duplicateof = Bug.id);

CREATE TRIGGER set_bug_number_of_duplicates_t
    AFTER INSERT OR UPDATE OR DELETE ON Bug
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_number_of_duplicates();

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 38, 0);

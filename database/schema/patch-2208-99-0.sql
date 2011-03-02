SET client_min_messages=ERROR;

BEGIN;
--Create new visible column on message.
ALTER TABLE Message
    ADD COLUMN visible BOOLEAN NOT NULL DEFAULT TRUE;

--Migrate the data
UPDATE Message
    SET visible = FALSE WHERE id IN
        (SELECT message FROM BugMessage WHERE visible = FALSE);

--And kill the old column
SELECT COUNT(id) FROM BugMessage;
ALTER TABLE BugMessage
    DROP COLUMN visible;

--Per patch adding reqs
INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
COMMIT;

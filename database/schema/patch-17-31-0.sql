SET client_min_messages = ERROR;

UPDATE Person SET displayname=name WHERE displayname IS NULL;
ALTER TABLE Person ALTER COLUMN displayname SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 31, 0);


SET client_min_messages=ERROR;

ALTER TABLE Manifest DROP COLUMN owner;

INSERT INTO LaunchpadDatabaseRevision VALUES (11,4,0);


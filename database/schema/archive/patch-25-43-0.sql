SET client_min_messages=ERROR;

ALTER TABLE Specification ALTER COLUMN specurl DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 43, 0);


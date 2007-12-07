SET client_min_messages=ERROR;

-- Default is 1 (Public)
ALTER TABLE Person 
ADD COLUMN visibility integer DEFAULT 1 NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);

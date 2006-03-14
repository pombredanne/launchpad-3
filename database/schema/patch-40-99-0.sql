SET client_min_messages=ERROR;

-- Ensure the DB matches the sqlobject class
ALTER TABLE binarypackagerelease ALTER COLUMN priority SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);

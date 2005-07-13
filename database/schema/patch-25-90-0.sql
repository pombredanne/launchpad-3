set client_min_messages=ERROR;

UPDATE Person SET timezone = 'UTC' WHERE timezone IS NULL;
ALTER TABLE Person ALTER COLUMN timezone SET DEFAULT 'UTC';
ALTER TABLE Person ALTER COLUMN timezone SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 90, 0);

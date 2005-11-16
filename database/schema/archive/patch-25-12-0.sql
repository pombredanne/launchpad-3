SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN karma integer;
ALTER TABLE Person ALTER COLUMN karma SET DEFAULT 0;
UPDATE Person SET karma=0;
ALTER TABLE Person ALTER COLUMN karma SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 12, 0);


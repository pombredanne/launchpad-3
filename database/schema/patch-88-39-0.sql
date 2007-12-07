SET client_min_messages=ERROR;

-- After rollout, we need to populate the existing entries with a '1' value.
-- This is to avoid downtime during rollout as Person is a slow table
-- to rewrite rows in, and allows us to do it in chunks avoiding bloat
-- on this critical table. Next cycle, we can add the desired NOT NULL
-- constraint and DEFAULT 1 to this column.
ALTER TABLE Person ADD COLUMN visibility integer;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 39, 0);


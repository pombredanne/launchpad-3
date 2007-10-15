SET client_min_messages=ERROR;

-- Urgent request from ddaa - ensure branch_type is set explicitly
ALTER TABLE Branch ALTER COLUMN branch_type SET DEFAULT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 32, 1);


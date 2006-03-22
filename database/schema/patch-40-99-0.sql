SET client_min_messages=ERROR;

ALTER TABLE BuildQueue ADD COLUMN manual boolean;
ALTER TABLE BuildQueue ALTER COLUMN manual SET DEFAULT FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);

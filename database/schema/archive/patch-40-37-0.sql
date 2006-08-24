SET client_min_messages=ERROR;

ALTER TABLE BuildQueue ADD COLUMN manual boolean;
ALTER TABLE BuildQueue ALTER COLUMN manual SET DEFAULT FALSE;
UPDATE BuildQueue SET manual = FALSE WHERE manual IS NULL;
ALTER TABLE BuildQueue ALTER COLUMN manual SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 37, 0);

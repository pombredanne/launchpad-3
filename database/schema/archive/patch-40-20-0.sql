SET client_min_messages=ERROR;

ALTER TABLE Build ADD COLUMN pocket integer;

UPDATE Build SET pocket = 0;

ALTER TABLE Build ALTER COLUMN pocket SET NOT NULL;

-- Temporarily keep API contranints, will be removed as soon as the
-- proper handling code gets merged.
ALTER TABLE Build ALTER COLUMN pocket SET DEFAULT 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 20, 0);


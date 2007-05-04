SET client_min_messages=ERROR;

ALTER TABLE DistroRelease
  ADD COLUMN hide_all_translations BOOLEAN DEFAULT TRUE NOT NULL;

-- The ones already in our database doesn't need to be hiden.
UPDATE DistroRelease
  SET hide_all_translations = FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);

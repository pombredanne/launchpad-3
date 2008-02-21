SET client_min_messages=ERROR;

ALTER TABLE DistroRelease
  ADD COLUMN hide_all_translations BOOLEAN DEFAULT TRUE NOT NULL;

-- The ones already in our database doesn't need to be hiden.
UPDATE DistroRelease
  SET hide_all_translations = FALSE;

-- Stuart asked me to add this here.
ALTER TABLE SpokenIn
  ADD CONSTRAINT spokenin__country__language__key UNIQUE (language, country);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 01, 0);

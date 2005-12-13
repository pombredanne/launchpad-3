
ALTER TABLE DistroReleaseQueue DROP COLUMN changesfile;
ALTER TABLE DistroReleaseQueue ADD COLUMN changesfilealias INTEGER;
ALTER TABLE DistroReleaseQueue ALTER COLUMN changesfilealias SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40,99,0);

SET client_min_messages=ERROR;

ALTER TABLE DistroReleaseQueue DROP COLUMN changesfile;
ALTER TABLE DistroReleaseQueue ADD COLUMN changesfile INTEGER;
ALTER TABLE DistroReleaseQueue ALTER COLUMN changesfile SET NOT NULL;
ALTER TABLE DistroReleaseQueue ADD CONSTRAINT
    distroreleasequeue_changesfile_fk
    FOREIGN KEY (changesfile) REFERENCES LibraryFileAlias;

INSERT INTO LaunchpadDatabaseRevision VALUES (40,10,0);

/*
 * Add pocket to distroreleasequeue and add a customformat queue item
 */
 
SET client_min_messages=ERROR;

ALTER TABLE DistroReleaseQueue ADD COLUMN pocket INTEGER;
UPDATE DistroReleaseQueue SET pocket=0;
ALTER TABLE DistroReleaseQueue ALTER COLUMN pocket SET NOT NULL;

CREATE TABLE DistroReleaseQueueCustom (
        id                 SERIAL  NOT NULL 
                           PRIMARY KEY,
        distroreleasequeue INTEGER NOT NULL 
                      CONSTRAINT distroreleasequeuecustom_distroreleasequeue_fk
                      REFERENCES DistroReleaseQueue(id),
        customformat       INTEGER NOT NULL,
        libraryfilealias   INTEGER NOT NULL 
                      CONSTRAINT distroreleasequeuecustom_libraryfilealias_fk
                      REFERENCES LibraryFileAlias(id)
        );

INSERT INTO LaunchpadDatabaseRevision VALUES (25,42,0);

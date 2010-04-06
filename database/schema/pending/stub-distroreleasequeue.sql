-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

/*
    Collapse DistreoReleaseQueue* into a single table, and add a date_created
    column while we are at it
*/

ALTER TABLE DistroReleaseQueue
    ADD COLUMN date_created timestamp WITHOUT TIME ZONE
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Columns from DistroReleaseQueueSource
ALTER TABLE DistroReleaseQueue
    ADD COLUMN sourcepackagerelease integer REFERENCES SourcePackageRelease;

-- Columns from DistroReleaseQueueBuild
ALTER TABLE DistroReleaseQueue
    ADD COLUMN build integer REFERENCES Build;

-- Columns from DistroReleaseQueueCustom
ALTER TABLE DistroReleaseQueue
    ADD COLUMN customformat integer;
-- XXX: What should this column be called? libraryfilealias is not descriptive
ALTER TABLE DistroReleaseQueue
    ADD COLUMN upload integer REFERENCES LibraryFileAlias;

-- Migrate and set data
-- XXX: This is currently being calculated programmatically. We either
-- need to duplicate this in the database patch, or we need a post rollout
-- migration script that sets date_created corretly.
UPDATE DistroReleaseQueue SET date_created = DEFAULT;
UPDATE DistroReleaseQueue
    SET sourcepackagerelease=DistroReleaseQueueSource.sourcepackagerelease
    FROM DistroReleaseQueueSource
    WHERE DistroReleaseQueue.id = DistroReleaseQueueSource.distroreleasequeue;
UPDATE DistroReleaseQueue
    SET build=DistroReleaseQueueBuild.build
    FROM DistroReleaseQueueBuild
    WHERE DistroReleaseQueue.id = DistroReleaseQueueBuild.distroreleasequeue;
UPDATE DistroReleaseQueue
    SET customformat=custom.customformat, upload=custom.libraryfilealias
    FROM DistroReleaseQueueCustom AS custom
    WHERE DistroReleaseQueue.id = custom.distroreleasequeue;

-- Set NOT NULL flags and other constraints now data has been migrated
ALTER TABLE DistroReleaseQueue ALTER COLUMN date_created SET NOT NULL;
ALTER TABLE DistroReleaseQueue ADD CONSTRAINT valid_custom_upload
    CHECK (customformat IS NULL = upload IS NULL);
-- XXX: Is this constraint valid? It says that only one of
-- (sourcepackagerelease,build,upload) may be set.
ALTER TABLE DistroReleaseQueue ADD CONSTRAINT valid_source_upload CHECK (
    (sourcepackagerelease IS NOT NULL AND build IS NULL AND upload IS NULL) OR
    (sourcepackagerelease IS NULL AND build IS NOT NULL AND upload IS NULL) OR
    (sourcepackagerelease IS NULL AND build IS NULL AND upload IS NOT NULL)
    );

-- Add some indexes
CREATE INDEX distroreleasequeue__upload__idx ON DistroReleaseQueue(upload)
    WHERE upload IS NOT NULL;
-- XXX: How is DistroRelaseQueue accessed? We need to know this to
-- setup indexes correctly.
CREATE INDEX distroreleasequeue__status__idx ON DistroReleaseQueue(status);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 44, 0);

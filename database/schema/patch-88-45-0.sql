SET client_min_messages=ERROR;

ALTER TABLE SourcePackageRelease
    RENAME COLUMN changelog to changelog_entry;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 45, 0);

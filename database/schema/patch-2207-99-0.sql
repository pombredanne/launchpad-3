SET client_min_messages=ERROR;

ALTER TABLE LibraryFileAlias
    ALTER COLUMN content DROP NOT NULL;

ALTER TABLE LibraryFileContent
    DROP COLUMN datemirrored,
    DROP COLUMN deleted;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);

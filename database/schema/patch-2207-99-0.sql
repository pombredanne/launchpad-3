SET client_min_messages=ERROR;

ALTER TABLE LibraryFileAlias
    ADD COLUMN deleted boolean DEFAULT FALSE NOT NULL,
    ALTER COLUMN content DROP NOT NULL;

CREATE INDEX libraryfilealias__deleted ON libraryfilealias(deleted);

ALTER TABLE LibraryFileContent
    DROP COLUMN datemirrored,
    DROP COLUMN deleted;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);

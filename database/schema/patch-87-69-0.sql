SET client_min_messages=ERROR;

ALTER TABLE LibraryFileAlias
    ADD COLUMN date_created timestamp WITHOUT TIME ZONE
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- For migation purpose, we set the date_created of the alias to
-- the one of its file content.
UPDATE LibraryFileAlias
    SET date_created = LibraryFileContent.datecreated
    FROM LibraryFileContent
    WHERE LibraryFileAlias.content = LibraryFileContent.id;

ALTER TABLE LibraryFileAlias ALTER COLUMN date_created SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 69, 0);

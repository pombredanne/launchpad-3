SET client_min_messages=ERROR;

ALTER TABLE LibraryFileAlias
    ADD COLUMN date_created timestamp WITHOUT TIME ZONE;
ALTER TABLE LibraryFileAlias ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 8, 0);

